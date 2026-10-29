"""Servidor real en un subproceso; se cierra siempre al finalizar las pruebas."""
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen


class ServidorPrueba:
    def __enter__(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            puerto = s.getsockname()[1]
        self.url = f"http://127.0.0.1:{puerto}"
        self.log = tempfile.TemporaryFile(mode="w+b")
        self.proceso = subprocess.Popen(
            [sys.executable, "-B", "-m", "uvicorn", "servidor.app:app", "--host", "127.0.0.1",
             "--port", str(puerto), "--workers", "1", "--log-level", "warning", "--ws-max-size", "32768"],
            cwd=Path(__file__).resolve().parents[1], stdout=self.log, stderr=self.log,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        limite = time.monotonic()+15
        while time.monotonic() < limite:
            try:
                with urlopen(self.url+"/health", timeout=.3) as respuesta:
                    if respuesta.status == 200:
                        return self
            except OSError:
                time.sleep(.05)
        self.proceso.terminate()
        self.proceso.wait(timeout=5)
        self.log.seek(0)
        raise RuntimeError(self.log.read().decode("utf-8", errors="replace"))

    def __exit__(self, *args):
        self.proceso.terminate()
        self.proceso.wait(timeout=5)
        self.log.close()
