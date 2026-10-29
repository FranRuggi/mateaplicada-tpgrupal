"""Integración de la vista real con dos roles y una carpeta temporal."""
import tempfile
import time
import unittest

import customtkinter as ctk

from gui.vistas.modo_archivo import VistaModoArchivo
from transporte.canal import CanalArchivo, Mensaje


class ModoRedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alice = VistaModoArchivo(self.root)
        self.bob = VistaModoArchivo(self.root)
        self.bob._cambiar_rol("Bob")

    def tearDown(self):
        self.alice.destroy()
        self.bob.destroy()
        self.root.update()
        self.tmp.cleanup()

    def conectar(self, vista):
        vista.entrada_carpeta.insert(0, self.tmp.name)
        vista._conectar()
        self.assertIsNotNone(vista.canal, vista.lbl_estado.cget("text"))

    def publicar(self):
        self.alice._poner_parametros(23, 5)
        self.alice._publicar_params_red()

    def test_conectar_no_descarta_mensajes_y_recibe_todo_el_lote(self):
        emisor = CanalArchivo(self.tmp.name)
        emisor.enviar(Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5}))
        emisor.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))
        self.conectar(self.bob)
        self.assertEqual(len(list(emisor.carpeta.glob("*.txt"))), 2)
        self.bob._verificar_mensajes()
        self.assertEqual((self.bob.yo.p, self.bob.yo.g, self.bob.yo.publica_ajena), (23, 5, 8))
        self.assertEqual(list(emisor.carpeta.glob("*.txt")), [])

    def test_intercambio_con_recepcion_automatica(self):
        self.conectar(self.alice)
        self.conectar(self.bob)
        self.publicar()
        self.assertEqual(self.alice.tarjeta.btn_publica.cget("state"), "normal")
        self.alice.yo.establecer_privada(6)
        self.alice.yo.calcular_publica()
        self.alice._enviar(self.alice.yo)
        limite = time.monotonic() + 3
        while self.bob.yo.publica_ajena is None and time.monotonic() < limite:
            self.root.update()
            time.sleep(0.01)
        self.assertEqual(self.bob.yo.publica_ajena, 8)
        self.bob.yo.establecer_privada(15)
        self.bob.yo.calcular_publica()
        self.bob._enviar(self.bob.yo)
        while self.alice.yo.publica_ajena is None and time.monotonic() < limite:
            self.root.update()
            time.sleep(0.01)
        self.assertEqual(self.alice.yo.derivar_secreto()[0], 2)
        self.assertEqual(self.bob.yo.derivar_secreto()[0], 2)

    def test_parametros_invalidos_se_apartan_sin_bloquear_el_siguiente(self):
        self.conectar(self.bob)
        emisor = CanalArchivo(self.tmp.name)
        emisor.enviar(Mensaje("Alice", "Bob", "PARAMETROS", {"p": 15, "g": 5}))
        emisor.enviar(Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5}))
        self.bob._verificar_mensajes()
        self.assertEqual(self.bob.yo.p, 23)
        self.assertEqual(len(list((emisor.carpeta / "rechazados").glob("*.txt"))), 1)

    def test_retransmision_no_borra_claves_y_cambio_publica_invalida_secreto(self):
        self.conectar(self.bob)
        emisor = CanalArchivo(self.tmp.name)
        parametros = Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5})
        emisor.enviar(parametros)
        emisor.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))
        self.bob._verificar_mensajes()
        self.bob.yo.establecer_privada(15)
        self.bob.yo.calcular_publica()
        self.bob.yo.derivar_secreto()
        emisor.enviar(parametros)
        emisor.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))
        self.bob._verificar_mensajes()
        self.assertEqual(self.bob.yo.secreto, 2)
        emisor.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 9}))
        self.bob._verificar_mensajes()
        self.assertIsNone(self.bob.yo.secreto)

    def test_desconectar_cancela_sondeo_y_cambiar_rol_reinicia_estado(self):
        self.conectar(self.alice)
        self.publicar()
        self.assertIsNotNone(self.alice._sondeo)
        self.alice._desconectar()
        self.assertIsNone(self.alice._sondeo)
        self.assertIsNone(self.alice.canal)
        self.assertIsNone(self.alice.yo.p)
        self.alice._cambiar_rol("Bob")
        self.assertEqual(self.alice.btn_pub_red.cget("state"), "disabled")

    def test_publica_adelantada_espera_a_parametros_sin_perderse(self):
        emisor = CanalArchivo(self.tmp.name)
        emisor.enviar(Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5}))
        ruta = next(emisor.carpeta.glob("*.txt"))
        temporal = ruta.with_suffix(".tmp")
        ruta.rename(temporal)
        emisor.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))
        self.conectar(self.bob)
        self.bob._verificar_mensajes()
        self.assertIsNone(self.bob.yo.p)
        self.assertEqual(len(list(emisor.carpeta.glob("*.txt"))), 1)
        temporal.rename(ruta)
        self.bob._verificar_mensajes()
        self.assertEqual(self.bob.yo.publica_ajena, 8)
        self.assertEqual(list(emisor.carpeta.glob("*.txt")), [])

    def test_carpeta_temporalmente_no_disponible_se_recupera(self):
        self.conectar(self.bob)
        emisor = CanalArchivo(self.tmp.name)
        emisor.enviar(Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5}))
        ruta = emisor.carpeta
        movida = ruta.with_name("interrumpida")
        ruta.rename(movida)
        self.bob._verificar_mensajes()
        self.assertIn("No se pudo acceder", self.bob.lbl_estado.cget("text"))
        movida.rename(ruta)
        self.bob._verificar_mensajes()
        self.assertEqual(self.bob.yo.p, 23)
        self.assertIn("Recepción automática activa", self.bob.lbl_estado.cget("text"))

    def test_publicar_sin_conexion_o_con_parametros_invalidos_muestra_error(self):
        self.alice._publicar_params_red()
        self.assertIn("Primero conectá", self.alice.lbl_estado.cget("text"))
        self.conectar(self.alice)
        self.alice._poner_parametros(15, 5)
        self.alice._publicar_params_red()
        self.assertIsNone(self.alice.yo.p)
        self.assertIn("no es primo", self.alice.lbl_estado.cget("text"))


if __name__ == "__main__":
    unittest.main()
