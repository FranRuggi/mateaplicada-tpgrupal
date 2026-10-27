"""
Canal de transporte: por dónde viajan los mensajes entre Alice y Bob.

Todas las implementaciones cumplen la misma interfaz (Canal), así la GUI
no sabe si los datos van por memoria, por archivos .txt o por sockets.

    CanalMemoria  -> LISTO. Modo local (las dos partes en la misma ventana).
    CanalArchivo  -> PENDIENTE. Objetivo principal de la consigna.
    CanalSocket   -> PENDIENTE. Objetivo secundario (dos computadoras).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable
import os

@dataclass
class Mensaje:
    remitente: str            # "Alice" / "Bob"
    destinatario: str
    tipo: str                 # "PARAMETROS" | "PUBLICA"
    datos: dict[str, int] = field(default_factory=dict)

    # Formato de texto plano que se escribe en el .txt / se manda por socket:
    #   de=Alice
    #   para=Bob
    #   tipo=PUBLICA
    #   A=123456
    def a_texto(self) -> str:
        lineas = [f"de={self.remitente}", f"para={self.destinatario}", f"tipo={self.tipo}"]
        lineas += [f"{k}={v}" for k, v in self.datos.items()]
        return "\n".join(lineas) + "\n"

    @staticmethod
    def desde_texto(texto: str) -> "Mensaje":
        campos = {}
        for linea in texto.strip().splitlines():
            if "=" not in linea:
                raise ValueError(f"Línea mal formada: {linea!r}")
            clave, valor = linea.split("=", 1)
            campos[clave.strip()] = valor.strip()
        datos = {k: int(v) for k, v in campos.items() if k not in ("de", "para", "tipo")}
        return Mensaje(campos["de"], campos["para"], campos["tipo"], datos)


class Canal(ABC):
    def __init__(self):
        self._observadores: list[Callable[[Mensaje], None]] = []

    def observar(self, callback: Callable[[Mensaje], None]):
        """Eve (y el log de la GUI) se suscriben acá: ven todo lo que pasa."""
        self._observadores.append(callback)

    def _notificar(self, mensaje: Mensaje):
        for cb in self._observadores:
            cb(mensaje)

    @abstractmethod
    def enviar(self, mensaje: Mensaje): ...

    @abstractmethod
    def recibir(self, destinatario: str) -> Mensaje | None:
        """Devuelve el próximo mensaje para `destinatario`, o None si no hay."""


class CanalMemoria(Canal):
    def __init__(self):
        super().__init__()
        self._cola: list[Mensaje] = []

    def enviar(self, mensaje: Mensaje):
        self._cola.append(mensaje)
        self._notificar(mensaje)

    def recibir(self, destinatario: str) -> Mensaje | None:
        for i, m in enumerate(self._cola):
            if m.destinatario == destinatario:
                return self._cola.pop(i)
        return None


class CanalArchivo(Canal):
    """TODO(transporte): escribir `<de>_a_<para>.txt` en una carpeta compartida
    con Mensaje.a_texto(), y en recibir() leer el archivo del otro si existe."""

    def __init__(self, carpeta: str):
        super().__init__()
        self.carpeta = carpeta

    def enviar(self, mensaje: Mensaje):
        #definir nombre del arch segun quien lo escribio y para quien
        nombre_archivo = f"{mensaje.remitente}_a_{mensaje.destinatario}.txt"
        ruta_archivo = os.path.join(self.carpeta, nombre_archivo)
        #guardar el mensaje a texto
        f = open(ruta_archivo, "w", encoding="utf-8")
        f.write(mensaje.a_texto())
        f.close()
        #notificar observadores del mensaje
        self._notificar(mensaje)

    def recibir(self, destinatario: str) -> Mensaje | None:
        #remitente: envia, si es para bob lo envio alice, sino alreves
        remitente = "Bob" if destinatario == "Alice" else "Alice"
        nombre_archivo = f"{remitente}_a_{destinatario}.txt"
        ruta_archivo = os.path.join(self.carpeta, nombre_archivo)
        #si existe la ruta del archivo
        if os.path.exists(ruta_archivo):
            f = open(ruta_archivo, "r", encoding="utf-8")
            contenido = f.read()
            f.close()
            os.remove(ruta_archivo)
            return Mensaje.desde_texto(contenido)
        return None


class CanalSocket(Canal):
    """TODO(transporte): uno escucha (servidor) y el otro se conecta (cliente).
    Mandar Mensaje.a_texto() terminado en una línea vacía."""

    def __init__(self, host: str, puerto: int, es_servidor: bool):
        super().__init__()
        self.host, self.puerto, self.es_servidor = host, puerto, es_servidor

    def enviar(self, mensaje: Mensaje):
        raise NotImplementedError("Canal por sockets todavía no implementado.")

    def recibir(self, destinatario: str) -> Mensaje | None:
        raise NotImplementedError("Canal por sockets todavía no implementado.")
