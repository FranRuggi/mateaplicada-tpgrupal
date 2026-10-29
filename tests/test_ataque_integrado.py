"""Eve ataca lo interceptado sin navegar ni consultar secretos de los actores."""
import threading
import time
import unittest
from unittest.mock import patch

from core import aritmetica
from gui.app import App


class ProgresoFuerzaBrutaTests(unittest.TestCase):
    def test_progreso_informa_intentos_y_restos_reales_hasta_el_limite(self):
        progreso = []
        resultado = aritmetica.log_discreto_fuerza_bruta(
            4, 5, 23, 10_001, al_progresar=lambda n, r: progreso.append((n, r)))
        self.assertEqual(resultado, (None, 10_001))
        self.assertEqual([n for n, _ in progreso], [5_000, 10_000, 10_001])
        for intentos, resto in progreso:
            self.assertEqual(resto, pow(4, intentos, 23))

    def test_cancelacion_cooperativa_no_se_presenta_como_limite_agotado(self):
        cancelar = threading.Event()
        resultado = aritmetica.log_discreto_fuerza_bruta(
            4, 5, 23, 1_000_000, cancelado=cancelar.is_set,
            al_progresar=lambda n, r: cancelar.set())
        self.assertEqual(resultado, (None, 5_000))

    def test_exito_conserva_la_api_anterior_y_notifica_el_intento_final(self):
        progreso = []
        self.assertEqual(aritmetica.log_discreto_fuerza_bruta(5, 8, 23, 100), (6, 6))
        aritmetica.log_discreto_fuerza_bruta(5, 8, 23, 100,
                                          al_progresar=lambda n, r: progreso.append((n, r)))
        self.assertEqual(progreso, [(6, 8)])


class AtaqueIntegradoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App()
        cls.app.withdraw()
        cls.errores_tk = []
        cls.app.report_callback_exception = lambda *e: cls.errores_tk.append(e)

    @classmethod
    def tearDownClass(cls):
        for identificador in cls.app.tk.call("after", "info"):
            cls.app.tk.call("after", "cancel", identificador)
        cls.app.destroy()

    def setUp(self):
        self.v = self.app.vistas["local"]
        self.v.reiniciar()
        self.v.escena.establecer_animaciones(False)
        self.p = self.v.ataque_eve
        self.p.sel_max.set("10 mil")
        self.app.mostrar("local")
        self.errores_tk.clear()

    def tearDown(self):
        self.v.reiniciar()
        self.assertEqual(self.errores_tk, [])

    def bombear(self, condicion, timeout=3):
        limite = time.monotonic()+timeout
        while not condicion() and time.monotonic() < limite:
            self.app.update()
            time.sleep(.01)
        self.assertTrue(condicion(), "La interfaz no terminó de procesar la búsqueda")

    def preparar(self, enviar_b=True, a=6, p=23, g=5):
        self.v.entrada_p.insert(0, str(p))
        self.v.entrada_g.insert(0, str(g))
        self.v._publicar_parametros()
        for tarjeta, privada in ((self.v.t_alice, a), (self.v.t_bob, 15)):
            tarjeta.entrada_priv.insert(0, str(privada))
            tarjeta.btn_publica.invoke()
        self.v.t_alice.btn_enviar.invoke()
        if enviar_b:
            self.v.t_bob.btn_enviar.invoke()

    def test_los_campos_se_completan_al_capturar_y_no_al_calcular_publicas(self):
        self.preparar(enviar_b=False)
        self.assertEqual(self.p.datos_publicos, {"p": 23, "g": 5, "A": 8})
        self.assertIsNone(self.p.campos["B"]._valor)
        self.v.escena.establecer_animaciones(True)
        self.v.t_bob.btn_enviar.invoke()
        self.assertNotIn("B", self.p.datos_publicos)
        self.assertEqual(self.p.btn.cget("state"), "disabled")
        self.v.escena.establecer_animaciones(False)
        self.assertEqual(self.p.campos["B"]._valor, 19)
        self.assertEqual(self.p.btn.cget("state"), "normal")

    def test_exito_en_la_misma_vista_y_k_derivada_sin_leer_privadas_o_secretos(self):
        self.preparar()
        # El objetivo interceptado sigue siendo A=8 aunque luego cambie la
        # privada del actor. Ninguno de los actores derivó su secreto todavía.
        self.v.alice.privada = 7
        self.v.btn_eve.invoke()
        self.bombear(lambda: not self.p._buscando)
        self.assertEqual(self.p._resultado.exponente, 6)
        self.assertEqual(self.p._resultado.intentos, 6)
        self.assertEqual(self.p._secreto, 2)
        self.assertIsNone(self.v.alice.secreto)
        self.assertIsNone(self.v.bob.secreto)
        self.assertEqual(self.v.winfo_manager(), "grid")
        self.assertNotEqual(self.app.vistas["eve"].winfo_manager(), "grid")
        canvas = self.v.escena.canvas
        self.assertEqual(canvas.itemcget(canvas.find_withtag("clave_Eve")[0], "text"), "K = 2")
        self.assertEqual(set(self.p.datos_publicos), {"p", "g", "A", "B"})

    def test_si_b_llega_despues_se_deriva_k_sin_repetir_la_busqueda(self):
        self.preparar(enviar_b=False)
        self.p.btn.invoke()
        self.bombear(lambda: not self.p._buscando)
        self.assertEqual(self.p._resultado.exponente, 6)
        self.assertIsNone(self.p._secreto)
        self.assertIn("Falta capturar B", self.p.lbl_resultado.cget("text"))
        with patch("gui.ataque_eve.aritmetica.log_discreto_fuerza_bruta", side_effect=AssertionError("B no requiere otra búsqueda")):
            self.v.t_bob.btn_enviar.invoke()
        self.assertEqual(self.p._secreto, 2)
        self.assertIn("K = 2", self.p.lbl_resultado.cget("text"))

    def test_limite_agotado_mantiene_el_secreto_desconocido_y_anima_a_eve(self):
        self.preparar(a=20_000, p=65_537, g=3)
        self.v.escena.establecer_animaciones(True)
        self.p.btn.invoke()
        self.bombear(lambda: not self.p._buscando)
        self.assertEqual(self.p.estado["estado"], "limite")
        self.assertEqual(self.p._resultado.intentos, 10_000)
        self.assertIsNone(self.p._resultado.exponente)
        self.assertIsNone(self.p._secreto)
        self.assertEqual(self.v.escena._evento.tipo, "ataque_limite")
        self.assertIsNone(self.v.escena._latido_id)
        self.assertIn("Se alcanzó el límite", self.p.lbl_resultado.cget("text"))

    def test_detener_una_busqueda_mantiene_la_ventana_respondiendo(self):
        self.preparar()
        self.v.escena.establecer_animaciones(True)
        entro = threading.Event()

        def busqueda(g, objetivo, p, maximo, cancelado, al_progresar):
            al_progresar(5_000, 7)
            entro.set()
            limite = time.monotonic()+3
            while not cancelado() and time.monotonic() < limite:
                time.sleep(.005)
            return None, 5_000

        with patch("gui.ataque_eve.aritmetica.log_discreto_fuerza_bruta", side_effect=busqueda):
            self.p.btn.invoke()
            self.assertTrue(entro.wait(1))
            self.bombear(lambda: self.p.estado.get("intentos") == 5_000)
            self.assertIsNotNone(self.v.escena._latido_id)
            self.assertEqual(self.p.btn_cancelar.cget("state"), "normal")
            self.p.btn_cancelar.invoke()
            self.bombear(lambda: not self.p._buscando)
        self.assertEqual(self.p.estado["estado"], "cancelado")
        self.assertIsNone(self.v.escena._latido_id)
        self.assertIn("detenida", self.p.lbl_resultado.cget("text"))
        self.assertIsNone(self.p._secreto)

    def test_reiniciar_no_deja_que_un_resultado_tardio_contamine_la_sesion(self):
        self.preparar()
        liberar, entro, termino = threading.Event(), threading.Event(), threading.Event()

        def busqueda(*args, **kw):
            entro.set()
            liberar.wait(2)
            termino.set()
            return 6, 6

        try:
            with patch("gui.ataque_eve.aritmetica.log_discreto_fuerza_bruta", side_effect=busqueda):
                self.p.btn.invoke()
                self.assertTrue(entro.wait(1))
                self.v.reiniciar()
                self.preparar()
                liberar.set()
                self.assertTrue(termino.wait(1))
                # El sondeo del helper vuelve al hilo de Tk a los 60 ms.
                fin = time.monotonic()+.15
                while time.monotonic() < fin:
                    self.app.update()
                    time.sleep(.01)
        finally:
            liberar.set()
        self.assertIsNone(self.p._resultado)
        self.assertIsNone(self.p._secreto)
        self.assertEqual(self.p.estado["estado"], "esperando")
        self.assertEqual(self.p.btn.cget("state"), "normal")

    def test_un_error_no_borra_el_diagnostico_ni_deja_buscando_la_escena(self):
        self.preparar()
        with patch("gui.ataque_eve.aritmetica.log_discreto_fuerza_bruta", side_effect=ValueError("fallo de prueba")):
            self.p.btn.invoke()
            self.bombear(lambda: not self.p._buscando)
        self.v._refrescar()
        self.assertIn("fallo de prueba", self.p.lbl_resultado.cget("text"))
        self.assertEqual(self.p.estado["estado"], "error")
        self.assertIsNone(self.v.escena._latido_id)
        self.assertEqual(self.p.btn.cget("state"), "normal")


if __name__ == "__main__":
    unittest.main()
