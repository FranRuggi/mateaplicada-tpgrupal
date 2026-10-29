"""Regresiones del intercambio: persistencia, orden, confirmación y procesos."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from transporte.canal import CanalArchivo, ErrorCanal, Mensaje


class CanalArchivoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.alice = CanalArchivo(self.tmp.name)
        self.bob = CanalArchivo(self.tmp.name)

    def parametros(self):
        return Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5})

    def test_varios_envios_no_se_sobrescriben_y_se_reciben_en_orden(self):
        mensajes = [self.parametros(), Mensaje("Alice", "Bob", "PUBLICA", {"A": 8})]
        for mensaje in mensajes:
            self.alice.enviar(mensaje)
        self.assertEqual(len(list(self.alice.carpeta.glob("*.txt"))), 2)
        for esperado in mensajes:
            recibido = self.bob.recibir("Bob")
            self.assertEqual(recibido, esperado)
            self.bob.confirmar(recibido)
        self.assertIsNone(self.bob.recibir("Bob"))

    def test_recibir_no_borra_y_reconectar_no_consume(self):
        self.alice.enviar(self.parametros())
        recibido = self.bob.recibir("Bob")
        self.assertIs(self.bob.recibir("Bob"), recibido)
        otro = CanalArchivo(self.tmp.name)
        self.assertEqual(otro.recibir("Bob"), recibido)
        self.assertEqual(len(list(otro.carpeta.glob("*.txt"))), 1)
        otro.confirmar(otro.recibir("Bob"))
        self.assertEqual(list(otro.carpeta.glob("*.txt")), [])

    def test_fallo_al_confirmar_conserva_el_mensaje(self):
        self.alice.enviar(self.parametros())
        mensaje = self.bob.recibir("Bob")
        with patch.object(Path, "unlink", side_effect=PermissionError("ocupado")):
            with self.assertRaises(PermissionError):
                self.bob.confirmar(mensaje)
        self.assertIs(self.bob.recibir("Bob"), mensaje)
        self.bob.confirmar(mensaje)

    def test_reinicio_del_emisor_y_retroceso_del_reloj_conservan_orden(self):
        with patch("transporte.canal.time.time_ns", return_value=10):
            self.alice.enviar(self.parametros())
        otro_emisor = CanalArchivo(self.tmp.name)
        with patch("transporte.canal.time.time_ns", return_value=1):
            otro_emisor.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))
        primero = self.bob.recibir("Bob")
        self.assertEqual(primero.tipo, "PARAMETROS")
        self.bob.confirmar(primero)
        self.assertEqual(self.bob.recibir("Bob").datos, {"A": 8})

    def test_sesiones_y_destinatarios_separados(self):
        self.alice.enviar(self.parametros())
        otra = CanalArchivo(self.tmp.name, "otro-grupo")
        self.assertIsNone(otra.recibir("Bob"))
        self.assertIsNone(self.alice.recibir("Alice"))
        self.bob.enviar(Mensaje("Bob", "Alice", "PUBLICA", {"B": 19}))
        self.assertEqual(self.alice.recibir("Alice").datos, {"B": 19})

    def test_ignora_temporales_y_no_hay_temporales_tras_enviar(self):
        (self.alice.carpeta / "Alice_a_Bob_incompleto.tmp").write_text("de=Alice", encoding="utf-8")
        self.assertIsNone(self.bob.recibir("Bob"))
        self.alice.enviar(self.parametros())
        self.assertEqual(len(list(self.alice.carpeta.glob("*.tmp"))), 1)
        self.assertIsNotNone(self.bob.recibir("Bob"))

    def test_archivo_malformado_se_aparta_y_el_siguiente_se_conserva(self):
        self.alice.enviar(self.parametros())
        primero = next(self.alice.carpeta.glob("*.txt"))
        primero.write_text("de=Alice\npara=Bob\ntipo=PUBLICA\na=6\n", encoding="utf-8")
        self.alice.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))
        with self.assertRaises(ErrorCanal):
            self.bob.recibir("Bob")
        self.assertTrue((self.alice.carpeta / "rechazados" / primero.name).exists())
        self.assertEqual(self.bob.recibir("Bob").datos, {"A": 8})

    def test_mensaje_con_destinatario_falso_se_aparta(self):
        self.alice.enviar(self.parametros())
        ruta = next(self.alice.carpeta.glob("*.txt"))
        ruta.write_text(Mensaje("Bob", "Alice", "PUBLICA", {"B": 19}).a_texto(), encoding="utf-8")
        with self.assertRaises(ErrorCanal):
            self.bob.recibir("Bob")

    def test_rechazar_conserva_evidencia_sin_bloquear_la_cola(self):
        self.alice.enviar(self.parametros())
        mensaje = self.bob.recibir("Bob")
        self.bob.rechazar(mensaje)
        self.assertIsNone(self.bob.recibir("Bob"))
        self.assertEqual(len(list((self.bob.carpeta / "rechazados").glob("*.txt"))), 1)

    def test_entradas_invalidas(self):
        for carpeta, sesion in (("", "demo"), (self.tmp.name, "../fuera"), (self.tmp.name, "")):
            with self.subTest(carpeta=carpeta, sesion=sesion), self.assertRaises(ValueError):
                CanalArchivo(carpeta, sesion)
        with self.assertRaises(ValueError):
            self.bob.recibir("Eve")
        with self.assertRaises(ValueError):
            Mensaje.desde_texto("de=Alice\npara=Bob\ntipo=PUBLICA\nA=8\nA=9\n")

    def test_posponer_permite_recibir_un_mensaje_anterior_que_llega_tarde(self):
        self.alice.enviar(self.parametros())
        ruta = next(self.alice.carpeta.glob("*.txt"))
        oculto = ruta.with_suffix(".tmp")
        ruta.rename(oculto)
        self.alice.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))
        publica = self.bob.recibir("Bob")
        self.bob.posponer(publica)
        oculto.rename(ruta)
        self.assertEqual(self.bob.recibir("Bob").tipo, "PARAMETROS")

    def test_intercambio_completo_entre_dos_procesos(self):
        programa = r'''
import json, sys, time
from protocolo.sesion import Participante
from transporte.canal import CanalArchivo, Mensaje
rol, carpeta = sys.argv[1:]
yo = Participante(rol)
canal = CanalArchivo(carpeta, 'procesos')
if rol == 'Alice':
    yo.establecer_parametros(23, 5)
    yo.establecer_privada(6)
    A, _ = yo.calcular_publica()
    canal.enviar(Mensaje('Alice', 'Bob', 'PARAMETROS', {'p': 23, 'g': 5}))
    canal.enviar(Mensaje('Alice', 'Bob', 'PUBLICA', {'A': A}))
limite = time.monotonic() + 10
while time.monotonic() < limite:
    mensaje = canal.recibir(rol)
    if mensaje is None:
        time.sleep(0.01)
        continue
    if mensaje.tipo == 'PARAMETROS':
        yo.establecer_parametros(mensaje.datos['p'], mensaje.datos['g'])
        yo.establecer_privada(15)
        B, _ = yo.calcular_publica()
        canal.enviar(Mensaje('Bob', 'Alice', 'PUBLICA', {'B': B}))
    else:
        yo.recibir_publica(next(iter(mensaje.datos.values())))
    canal.confirmar(mensaje)
    if yo.publica_ajena is not None:
        K, _ = yo.derivar_secreto()
        print(json.dumps({'rol': rol, 'K': K}))
        break
else:
    raise RuntimeError('No se completó el intercambio')
'''
        raiz = Path(__file__).resolve().parents[1]
        procesos = [subprocess.Popen([sys.executable, "-B", "-c", programa, rol, self.tmp.name],
                                    cwd=raiz, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding="utf-8") for rol in ("Alice", "Bob")]
        try:
            for proceso in procesos:
                salida, error = proceso.communicate(timeout=15)
                self.assertEqual(proceso.returncode, 0, error)
                self.assertEqual(json.loads(salida)["K"], 2)
        finally:
            for proceso in procesos:
                if proceso.poll() is None:
                    proceso.kill()
                    proceso.communicate()


if __name__ == "__main__":
    unittest.main()
