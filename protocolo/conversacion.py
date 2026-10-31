"""Conversación cifrada independiente de Tk y del medio de transporte.

El contexto autenticado une cada sobre con su intercambio, sus datos DH,
su dirección y su identificador. Ninguna clave se agrega al mensaje público.
"""
from dataclasses import dataclass, field
import hashlib
import json
from uuid import uuid4

from core.cifrado import ErrorCifrado
from protocolo.mensajes_cifrados import MensajeCifrado, cifrar_mensaje, descifrar_mensaje
from transporte.canal import Mensaje

MAX_MENSAJES = 200


@dataclass
class RegistroMensaje:
    mensaje: Mensaje
    sobre: MensajeCifrado
    texto_propio: str | None = None
    lecturas: dict = field(default_factory=dict)
    _claves: dict = field(default_factory=dict, repr=False)


class Conversacion:
    def __init__(self):
        self.intercambio = ""
        self.publicos = {}
        self.registros: list[RegistroMensaje] = []

    @property
    def lista(self):
        return bool(self.intercambio) and set(self.publicos) == {"p", "g", "A", "B"}

    def actualizar(self, publicos, intercambio):
        datos = {k: publicos[k] for k in ("p", "g", "A", "B") if k in publicos}
        if (self.intercambio, self.publicos) != (intercambio, datos):
            self.registros.clear()
            self.publicos = datos
            self.intercambio = intercambio

    def _contexto(self, m):
        huella = hashlib.sha256(json.dumps(
            {k: str(v) for k, v in self.publicos.items()}, sort_keys=True).encode()).hexdigest()
        return json.dumps({"intercambio": self.intercambio, "publicos": huella,
                           "de": m.remitente, "para": m.destinatario,
                           "id": m.datos["id"]}, sort_keys=True, separators=(",", ":")).encode()

    def preparar(self, rol, texto, secreto):
        if not self.lista:
            raise ValueError("Primero intercambien p, g, A y B por el canal.")
        if len(self.registros) >= MAX_MENSAJES:
            raise ValueError("La conversación llegó a 200 mensajes. Inicien otro intercambio.")
        m = Mensaje(rol, "Bob" if rol == "Alice" else "Alice", "CIFRADO",
                    {"id": uuid4().hex}, self.intercambio)
        m.datos["sobre"] = cifrar_mensaje(texto, secreto, contexto=self._contexto(m)).a_texto()
        m.validar()
        return m

    def registrar(self, m, texto_propio=None):
        m.validar()
        if m.tipo != "CIFRADO" or not self.lista or m.intercambio != self.intercambio:
            raise ValueError("El mensaje cifrado pertenece a otro intercambio o faltan datos públicos.")
        for registro in self.registros:
            if registro.mensaje.datos["id"] == m.datos["id"]:
                if registro.mensaje != m:
                    raise ValueError("Identificador de mensaje reutilizado con otro contenido.")
                return registro
        if len(self.registros) >= MAX_MENSAJES:
            raise ValueError("La conversación llegó a 200 mensajes.")
        # Copia para que cambios posteriores en el transporte no alteren el historial.
        copia = Mensaje(m.remitente, m.destinatario, m.tipo, dict(m.datos), m.intercambio)
        registro = RegistroMensaje(copia, MensajeCifrado.desde_texto(m.datos["sobre"]), texto_propio)
        self.registros.append(registro)
        return registro

    def pendientes(self, rol):
        """Sobres recibidos que este actor todavía no intentó descifrar."""
        return [r for r in self.registros
                if r.mensaje.destinatario == rol and r.lecturas.get(rol) is None]

    def _leer(self, registro, lector, secreto):
        registro._claves[lector] = secreto
        try:
            resultado = descifrar_mensaje(registro.sobre, secreto,
                                         contexto=self._contexto(registro.mensaje))
        except ErrorCifrado:
            resultado = ErrorCifrado("No se pudo autenticar: K o contenido incorrectos.")
        registro.lecturas[lector] = resultado
        return registro, lector, resultado

    def actualizar_claves(self, claves, secreto_eve=None):
        """Invalidar lecturas si cambia K, sin descifrar mensajes de Alice/Bob.

        Eve sí intenta leer con la K de su ataque. La GUI recibe solo los
        intentos nuevos, de modo que la consola no los repita al refrescar.
        """
        nuevas = []
        for r in self.registros:
            lector = r.mensaje.destinatario
            clave = claves.get(lector)
            if lector not in r._claves or r._claves[lector] != clave:
                r._claves[lector] = clave
                r.lecturas[lector] = None
            if "Eve" not in r._claves or r._claves["Eve"] != secreto_eve:
                r._claves["Eve"] = secreto_eve
                r.lecturas["Eve"] = None
                if secreto_eve is not None:
                    nuevas.append(self._leer(r, "Eve", secreto_eve))
        return nuevas

    def descifrar(self, identificador, rol, secreto):
        """Acción explícita del destinatario para un único mensaje recibido."""
        if type(secreto) is not int or secreto <= 0 or secreto.bit_length() > 4096:
            raise ValueError("Primero derivá tu secreto K para descifrar el mensaje.")
        r = next((r for r in self.registros if r.mensaje.datos["id"] == identificador), None)
        if r is None or r.mensaje.destinatario != rol:
            raise ValueError("El mensaje no está dirigido a este participante.")
        if r.lecturas.get(rol) is not None and r._claves.get(rol) == secreto:
            return []
        return [self._leer(r, rol, secreto)]

    def descifrar_pendientes(self, claves, secreto_eve=None):
        """API de lectura por lote; la GUI usa descifrar() al pulsar el botón."""
        nuevas = self.actualizar_claves(claves, secreto_eve)
        for rol, secreto in claves.items():
            if secreto is not None:
                for r in self.pendientes(rol):
                    nuevas.extend(self.descifrar(r.mensaje.datos["id"], rol, secreto))
        return nuevas
