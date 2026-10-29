"""Dos interfaces reales contra un servidor real, desde la sala hasta K y Eve."""
import time
import unittest
from unittest.mock import patch

import customtkinter as ctk

from gui.vistas.internet import VistaInternet
from servidor_prueba import ServidorPrueba


class PartidaInternetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = ServidorPrueba().__enter__()
        cls.root = ctk.CTk()
        cls.root.withdraw()
        cls.errores = []
        cls.root.report_callback_exception = lambda *e: cls.errores.append(e)

    @classmethod
    def tearDownClass(cls):
        for identificador in cls.root.tk.call("after", "info"):
            cls.root.tk.call("after", "cancel", identificador)
        cls.root.destroy()
        cls.servidor.__exit__()

    def setUp(self):
        self.a, self.b = VistaInternet(self.root), VistaInternet(self.root)
        self.errores.clear()
        for vista in (self.a, self.b):
            vista.entrada_servidor.delete(0, "end")
            vista.entrada_servidor.insert(0, self.servidor.url)

    def tearDown(self):
        self.a.destroy()
        self.b.destroy()
        self.root.update()
        self.assertEqual(self.errores, [])

    def esperar(self, condicion):
        limite = time.monotonic()+15
        while not condicion() and time.monotonic() < limite:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(condicion(), "No se completó el flujo de sala")

    def entrar(self):
        for vista in (self.a, self.b):
            self.assertEqual(vista.paso_actual, "sala")
            self.assertEqual(vista.paso_sala.winfo_manager(), "grid")
            self.assertEqual(vista.paso_personaje.winfo_manager(), "")
        self.a.btn_crear.invoke()
        self.esperar(lambda: self.a.estado is not None)
        self.assertEqual(self.a.paso_actual, "personaje")
        self.assertEqual(self.a.paso_sala.winfo_manager(), "")
        self.assertEqual(self.a.paso_personaje.winfo_manager(), "grid")
        codigo = self.a.estado["sala"]
        self.b.entrada_codigo.insert(0, codigo)
        self.b.btn_unir.invoke()
        self.esperar(lambda: self.b.estado is not None)
        self.assertEqual(self.b.paso_actual, "personaje")
        self.a.botones_rol["Alice"].invoke()
        self.esperar(lambda: self.b.estado["roles"]["Alice"])
        self.assertEqual(self.a.paso_actual, "personaje")
        self.assertIsNone(self.a.partida)
        self.assertEqual(self.b.botones_rol["Alice"].cget("state"), "disabled")
        self.assertEqual(self.b.botones_rol["Bob"].cget("state"), "normal")
        self.b.botones_rol["Bob"].invoke()
        self.esperar(lambda: self.a.partida is not None and self.b.partida is not None)
        for vista in (self.a, self.b):
            self.assertEqual(vista.paso_actual, "partida")
            self.assertEqual(vista.lobby.grid_info(), {})
            self.assertEqual(vista.partida.winfo_manager(), "grid")
            vista.partida.escena.establecer_animaciones(False)
        return self.a.partida, self.b.partida

    def test_intercambio_desde_tarjetas_con_privadas_aisladas_y_ataque_integrado(self):
        a, b = self.entrar()
        self.assertEqual(a.partida, b.partida)
        self.assertTrue(a.t_bob.solo_lectura)
        self.assertTrue(b.t_alice.solo_lectura)
        self.assertFalse(hasattr(b.t_alice, "entrada_priv"))
        self.assertEqual(b.btn_publicar.cget("state"), "disabled")
        a.entrada_p.insert(0, "23")
        a.entrada_g.insert(0, "5")
        with patch("gui.vistas.modo_local.tema.correr_en_hilo") as generacion:
            a._generar_parametros()
        resultado_tardio = generacion.call_args.args[2]
        a.btn_publicar.invoke()
        resultado_tardio((47, 5, []))
        self.assertEqual(a.entrada_p.get(), "23")
        self.esperar(lambda: a.yo.p == 23 and b.yo.p == 23)
        for partida, privada in ((a, 6), (b, 15)):
            partida.tarjeta.entrada_priv.insert(0, str(privada))
            partida.tarjeta.btn_publica.invoke()
            partida.tarjeta.btn_enviar.invoke()
        self.esperar(lambda: a._secuencia == 3 and b._secuencia == 3)
        self.assertIsNone(a.otro.privada)
        self.assertIsNone(b.otro.privada)
        self.assertEqual(a.otro.publica, 19)
        self.assertEqual(b.otro.publica, 8)
        for partida in (a, b):
            partida.tarjeta.btn_secreto.invoke()
            self.assertEqual(partida.yo.secreto, 2)
            self.assertIsNone(partida.otro.secreto)
            self.assertEqual(partida.datos_para_eve(), {"p": 23, "g": 5, "A": 8})
        b.btn_eve.invoke()
        self.esperar(lambda: not b.ataque_eve._buscando)
        self.assertEqual(b.ataque_eve._resultado.exponente, 6)
        self.assertEqual(b.ataque_eve._secreto, 2)
        a.colocar_registro("Derecha")
        self.assertIn("A = 8", a.consola.get("1.0", "end"))

    def test_al_salir_un_jugador_vuelve_la_sala_y_se_libera_su_personaje(self):
        a, _ = self.entrar()
        codigo = self.a.estado["sala"]
        self.b.salir()
        self.esperar(lambda: self.a.partida is None)
        self.assertEqual(self.a.paso_actual, "personaje")
        self.assertEqual(self.a.paso_sala.winfo_manager(), "")
        self.assertEqual(self.a.paso_personaje.winfo_manager(), "grid")
        self.assertEqual(self.b.paso_actual, "sala")
        self.assertEqual(self.a.estado["rol"], "Alice")
        self.assertFalse(self.a.estado["roles"]["Bob"])
        self.assertEqual(self.a.datos_para_eve(), {})
        self.assertIn("reservado", self.a.lbl_estado.cget("text"))
        self.b.entrada_codigo.delete(0, "end")
        self.b.entrada_codigo.insert(0, codigo)
        self.b.btn_unir.invoke()
        self.esperar(lambda: self.b.estado is not None)
        self.b.botones_rol["Bob"].invoke()
        self.esperar(lambda: self.a.partida is not None and self.b.partida is not None)
        self.assertNotEqual(self.a.partida.partida, a.partida)
        self.assertIsNone(self.a.partida.yo.p)

    def test_error_de_sala_no_existente_permite_reintentar(self):
        self.a.entrada_codigo.insert(0, "ZZZZZZZZ")
        self.a.btn_unir.invoke()
        self.esperar(lambda: "no existe" in self.a.lbl_estado.cget("text"))
        self.assertIsNone(self.a.cliente)
        self.assertEqual(self.a.btn_crear.cget("state"), "normal")
        self.assertEqual(self.a.paso_actual, "sala")
        self.assertEqual(self.a.paso_personaje.winfo_manager(), "")

    def test_puede_cancelar_la_conexion_sin_mostrar_la_eleccion_antes_de_entrar(self):
        with patch("gui.vistas.internet.ClienteSalas") as cliente:
            self.a.btn_crear.invoke()
            self.assertEqual(self.a.paso_actual, "sala")
            self.assertEqual(self.a.paso_personaje.winfo_manager(), "")
            self.assertEqual(self.a.btn_cancelar.winfo_manager(), "grid")
            self.a.elegir("Alice")
            cliente.return_value.enviar.assert_not_called()
            self.a.btn_cancelar.invoke()
            cliente.return_value.cerrar.assert_called_once()
        self.assertIsNone(self.a.cliente)
        self.assertEqual(self.a.paso_actual, "sala")
        self.assertEqual(self.a.btn_cancelar.winfo_manager(), "")
        self.assertEqual(self.a.btn_crear.cget("state"), "normal")


if __name__ == "__main__":
    unittest.main()
