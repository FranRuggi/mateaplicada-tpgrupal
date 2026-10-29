"""
Canal de transporte: por dónde viajan los mensajes entre Alice y Bob.

Todas las implementaciones cumplen la misma interfaz (Canal), así la GUI
no sabe si los datos van por memoria, por archivos .txt o por sockets.

    CanalMemoria  -> LISTO. Modo local (las dos partes en la misma ventana).
    CanalArchivo  -> Cola por archivos, con confirmación y sesiones.
    CanalSocket   -> PENDIENTE. Objetivo secundario (dos computadoras).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable
import os
from pathlib import Path
import re
import time
from uuid import uuid4


class ErrorCanal(Exception):
    """Error de transporte que se puede mostrar al usuario."""

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
        self.validar()
        lineas = [f"de={self.remitente}", f"para={self.destinatario}", f"tipo={self.tipo}"]
        lineas += [f"{k}={v}" for k, v in self.datos.items()]
        return "\n".join(lineas) + "\n"

    @staticmethod
    def desde_texto(texto: str) -> "Mensaje":
        if len(texto) > 16_384:
            raise ValueError("El mensaje es demasiado grande.")
        campos = {}
        for linea in texto.strip().splitlines():
            if "=" not in linea:
                raise ValueError(f"Línea mal formada: {linea!r}")
            clave, valor = linea.split("=", 1)
            clave = clave.strip()
            if clave in campos:
                raise ValueError(f"Campo repetido: {clave}.")
            campos[clave] = valor.strip()
        if not {"de", "para", "tipo"} <= campos.keys():
            raise ValueError("Faltan de, para o tipo en el mensaje.")
        try:
            datos = {k: int(v) for k, v in campos.items() if k not in ("de", "para", "tipo")}
        except ValueError as e:
            raise ValueError("Los datos públicos deben ser números enteros.") from e
        mensaje = Mensaje(campos["de"], campos["para"], campos["tipo"], datos)
        mensaje.validar()
        return mensaje

    def validar(self):
        if {self.remitente, self.destinatario} != {"Alice", "Bob"}:
            raise ValueError("El mensaje debe circular entre Alice y Bob.")
        if self.tipo == "PARAMETROS" and self.remitente == "Alice":
            esperados = {"p", "g"}
        elif self.tipo == "PUBLICA":
            esperados = {"A" if self.remitente == "Alice" else "B"}
        else:
            raise ValueError("Tipo de mensaje o remitente no permitido.")
        if set(self.datos) != esperados or any(type(v) is not int for v in self.datos.values()):
            raise ValueError("El mensaje no contiene los datos públicos esperados.")


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
    """Una cola por sesión, con un consumidor por rol.

    recibir() conserva el archivo. El consumidor llama confirmar() después de
    aplicar el mensaje o rechazar() si es inválido. Los .tmp no se reciben.
    """

    def __init__(self, carpeta: str, sesion: str = "demo"):
        super().__init__()
        if not carpeta.strip():
            raise ValueError("Elegí una carpeta compartida.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", sesion):
            raise ValueError("La sesión admite 1 a 48 letras, números, guiones o guiones bajos.")
        base = Path(carpeta).expanduser().resolve()
        if not base.is_dir():
            raise ValueError("La carpeta compartida no existe o no está disponible.")
        self.sesion = sesion
        self.carpeta = base / "sesiones" / sesion
        self.carpeta.mkdir(parents=True, exist_ok=True)
        # Comprobar escritura sin consumir ningún mensaje pendiente.
        prueba = self.carpeta / f".{uuid4().hex}.tmp"
        try:
            with prueba.open("x", encoding="utf-8"):
                pass
        finally:
            prueba.unlink(missing_ok=True)
        self._ultimo = 0
        self._pendientes: dict[str, tuple[Mensaje, Path]] = {}

    def _archivos(self, remitente: str, destinatario: str) -> list[Path]:
        if not self.carpeta.is_dir():
            raise FileNotFoundError("La carpeta de la sesión no está disponible.")
        patron = re.compile(rf"{remitente}_a_{destinatario}_(\d{{20}})_[0-9a-f]{{32}}\.txt")
        return sorted(p for p in self.carpeta.glob(f"{remitente}_a_{destinatario}_*.txt")
                      if patron.fullmatch(p.name))

    def enviar(self, mensaje: Mensaje):
        texto = mensaje.a_texto()
        anteriores = self._archivos(mensaje.remitente, mensaje.destinatario)
        ultimo_pendiente = int(anteriores[-1].stem.split("_")[-2]) if anteriores else 0
        # Mantener el orden incluso si el reloj retrocede o se reinicia el emisor.
        self._ultimo = max(time.time_ns(), self._ultimo + 1, ultimo_pendiente + 1)
        nombre = f"{mensaje.remitente}_a_{mensaje.destinatario}_{self._ultimo:020d}_{uuid4().hex}"
        temporal = self.carpeta / f"{nombre}.tmp"
        destino = self.carpeta / f"{nombre}.txt"
        try:
            with temporal.open("x", encoding="utf-8", newline="\n") as archivo:
                archivo.write(texto)
                archivo.flush()
                os.fsync(archivo.fileno())
            os.replace(temporal, destino)
        finally:
            temporal.unlink(missing_ok=True)
        self._notificar(mensaje)

    def recibir(self, destinatario: str) -> Mensaje | None:
        if destinatario not in ("Alice", "Bob"):
            raise ValueError("El destinatario debe ser Alice o Bob.")
        if destinatario in self._pendientes:
            return self._pendientes[destinatario][0]
        remitente = "Bob" if destinatario == "Alice" else "Alice"
        archivos = self._archivos(remitente, destinatario)
        if not archivos:
            return None
        ruta = archivos[0]
        try:
            if ruta.stat().st_size > 16_384:
                raise ValueError("El mensaje es demasiado grande.")
            mensaje = Mensaje.desde_texto(ruta.read_text(encoding="utf-8"))
            if (mensaje.remitente, mensaje.destinatario) != (remitente, destinatario):
                raise ValueError("El contenido no coincide con el destinatario del archivo.")
        except (ValueError, UnicodeError) as e:
            self._apartar(ruta)
            raise ErrorCanal(f"Mensaje inválido apartado en 'rechazados': {e}") from e
        self._pendientes[destinatario] = (mensaje, ruta)
        return mensaje

    def _ruta_pendiente(self, mensaje: Mensaje) -> Path:
        pendiente = self._pendientes.get(mensaje.destinatario)
        if pendiente is None or pendiente[0] is not mensaje:
            raise ValueError("El mensaje no está pendiente de confirmación en este canal.")
        return pendiente[1]

    def confirmar(self, mensaje: Mensaje):
        """Retirar solo después de procesar correctamente el mensaje."""
        self._ruta_pendiente(mensaje).unlink(missing_ok=True)
        del self._pendientes[mensaje.destinatario]

    def posponer(self, mensaje: Mensaje):
        """Conservarlo y volver a ordenar la cola en el próximo intento."""
        self._ruta_pendiente(mensaje)
        del self._pendientes[mensaje.destinatario]

    def rechazar(self, mensaje: Mensaje):
        """Apartar un mensaje que no puede aplicarse al protocolo."""
        self._apartar(self._ruta_pendiente(mensaje))
        del self._pendientes[mensaje.destinatario]

    def _apartar(self, ruta: Path):
        rechazados = self.carpeta / "rechazados"
        rechazados.mkdir(exist_ok=True)
        ruta.replace(rechazados / ruta.name)


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
