"""Cliente WebSocket: toda la E/S ocurre fuera del hilo de Tk."""
import json
import os
from pathlib import Path
import queue
import sys
import ssl
import threading
import time
from urllib.parse import urlsplit, urlunsplit

from websockets.sync.client import connect
from websockets.exceptions import InvalidStatus

from transporte.canal import ErrorCanal


def url_predeterminada():
    if os.environ.get("DH_SERVER_URL"):
        return os.environ["DH_SERVER_URL"]
    raiz = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    try:
        datos = json.loads((raiz / "configuracion.json").read_text(encoding="utf-8"))
        return str(datos.get("servidor_url", ""))
    except (OSError, ValueError, TypeError):
        return ""


def url_websocket(url):
    partes = urlsplit(url.strip())
    esquema = {"http": "ws", "https": "wss", "ws": "ws", "wss": "wss"}.get(partes.scheme)
    if not esquema or not partes.hostname or partes.username or partes.password or partes.query or partes.fragment:
        raise ValueError("Ingresá la dirección https:// del servidor de salas.")
    if partes.path not in ("", "/", "/ws"):
        raise ValueError("Usá la dirección del servidor, sin rutas adicionales.")
    return urlunsplit((esquema, partes.netloc, "/ws", "", ""))


class ClienteSalas:
    def __init__(self, url):
        self.url = url_websocket(url)
        self.eventos = queue.SimpleQueue()
        self._salientes = queue.Queue(maxsize=64)
        self._cerrar = threading.Event()
        self._abierto = threading.Event()
        self._hilo = None

    def conectar(self):
        if self._hilo is not None:
            return
        self._hilo = threading.Thread(target=self._trabajar, daemon=True)
        self._hilo.start()

    def enviar(self, accion, **datos):
        if self._cerrar.is_set() or not self._abierto.is_set():
            raise ErrorCanal("Todavía no hay conexión con el servidor.")
        try:
            self._salientes.put_nowait({"accion": accion, **datos})
        except queue.Full as error:
            raise ErrorCanal("Hay demasiados envíos pendientes. Esperá un momento.") from error

    def cerrar(self):
        self._cerrar.set()

    def _abrir(self, opciones):
        limite, demora = time.monotonic()+90, .5
        while not self._cerrar.is_set():
            try:
                return connect(self.url, **opciones)
            except Exception as e:
                transitorio = (isinstance(e, OSError) and not isinstance(e, ssl.SSLCertVerificationError)) or (
                    isinstance(e, InvalidStatus) and e.response.status_code in (200, 429, 502, 503, 504))
                restante = limite-time.monotonic()
                if not transitorio or restante <= 0:
                    raise
                self.eventos.put({"evento": "conectando", "mensaje": "Esperando a que el servidor esté disponible…"})
                self._cerrar.wait(min(demora, restante))
                demora = min(demora*2, 5)
        return None

    def _trabajar(self):
        error = "Se perdió la conexión. Volvé a ingresar a una sala."
        try:
            opciones = {"open_timeout": 10, "close_timeout": 1,
                        "ping_interval": 20, "ping_timeout": 20, "max_size": 32_768}
            if urlsplit(self.url).hostname in ("localhost", "127.0.0.1", "::1"):
                opciones["proxy"] = None
            conexion = self._abrir(opciones)
            if conexion is None:
                return
            with conexion as ws:
                if self._cerrar.is_set():
                    return
                self._abierto.set()
                self.eventos.put({"evento": "conectado"})
                ultimo_ping = time.monotonic()
                while not self._cerrar.is_set():
                    for _ in range(20):
                        try:
                            pedido = self._salientes.get_nowait()
                        except queue.Empty:
                            break
                        ws.send(json.dumps(pedido, ensure_ascii=False))
                    if time.monotonic()-ultimo_ping >= 25:
                        ws.send('{"accion":"ping"}')
                        ultimo_ping = time.monotonic()
                    try:
                        recibido = ws.recv(timeout=.1)
                    except TimeoutError:
                        continue
                    mensaje = json.loads(recibido)
                    if not isinstance(mensaje, dict):
                        raise ValueError("Respuesta inválida del servidor.")
                    self.eventos.put(mensaje)
        except Exception as e:
            error = f"No se pudo mantener la conexión: {e}"
        finally:
            self._abierto.clear()
            if not self._cerrar.is_set():
                self.eventos.put({"evento": "desconectado", "mensaje": error})
