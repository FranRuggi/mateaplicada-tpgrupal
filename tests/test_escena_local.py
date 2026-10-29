"""La escena acompaña al protocolo real, incluso al reiniciar durante un envío."""
import unittest
from unittest.mock import patch

from gui.app import App
from transporte.canal import Mensaje


class EscenaLocalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App()
        cls.app.withdraw()
        cls.errores_tk = []
        cls.app.report_callback_exception = lambda *error: cls.errores_tk.append(error)

    @classmethod
    def tearDownClass(cls):
        for identificador in cls.app.tk.call("after", "info"):
            cls.app.tk.call("after", "cancel", identificador)
        cls.app.destroy()

    def setUp(self):
        self.v = self.app.vistas["local"]
        self.v.reiniciar()
        self.v.escena.establecer_animaciones(False)
        self.errores_tk.clear()

    def tearDown(self):
        self.v.reiniciar()
        self.assertEqual(self.errores_tk, [])

    def parametros(self, p=23, g=5):
        self.v.entrada_p.insert(0, str(p))
        self.v.entrada_g.insert(0, str(g))
        self.v._publicar_parametros()

    def calcular(self, a=6, b=15):
        for tarjeta, valor in ((self.v.t_alice, a), (self.v.t_bob, b)):
            tarjeta.entrada_priv.insert(0, str(valor))
            tarjeta.btn_publica.invoke()

    def completar_animaciones(self):
        escena = self.v.escena
        for _ in range(10):
            if not escena.en_animacion:
                break
            escena._cancelar_reloj()
            escena._inicio -= 3
            escena._avanzar()
        self.assertFalse(escena.en_animacion)

    def texto_canvas(self, etiqueta):
        c = self.v.escena.canvas
        return c.itemcget(c.find_withtag(etiqueta)[0], "text")

    def test_intercambio_desde_controles_calcula_y_muestra_el_secreto_real(self):
        self.parametros()
        self.calcular()
        self.assertEqual((self.v.alice.publica, self.v.bob.publica), (8, 19))
        self.assertNotIn("A", self.v.escena.publicos_observados)
        self.v.t_alice.btn_enviar.invoke()
        self.v.t_bob.btn_enviar.invoke()
        self.v.t_alice.btn_secreto.invoke()
        self.v.t_bob.btn_secreto.invoke()
        self.assertEqual((self.v.alice.secreto, self.v.bob.secreto), (2, 2))
        self.assertEqual(self.texto_canvas("clave_Alice"), "K = 2")
        self.assertEqual(self.texto_canvas("clave_Bob"), "K = 2")
        self.assertEqual(self.texto_canvas("clave_Eve"), "K = ?")
        self.assertEqual(self.v.escena.publicos_observados, {"p": 23, "g": 5, "A": 8, "B": 19})
        self.assertIn("MISMA".lower(), self.v.banner.cget("text").lower())

    def test_eve_no_recibe_privadas_ni_secretos_al_calcularlos_o_mostrarlos(self):
        self.parametros()
        self.calcular()
        self.v.t_alice._alternar_ver()
        self.v.t_bob._alternar_ver()
        self.v.t_alice.btn_enviar.invoke()
        self.v.t_bob.btn_enviar.invoke()
        self.v.t_alice.btn_secreto.invoke()
        self.assertEqual(set(self.v.eve_sabe), {"p", "g", "A", "B"})
        self.assertEqual(self.v.datos_para_eve(), {"p": 23, "g": 5, "A": 8})
        self.assertEqual(set(self.v.escena.publicos_observados), {"p", "g", "A", "B"})

    def test_cola_visual_copia_los_mensajes_y_conserva_ambos_sentidos(self):
        escena = self.v.escena
        escena.establecer_animaciones(True)
        parametros = Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5})
        escena.mostrar_mensaje(parametros)
        escena.mostrar_mensaje(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))
        escena.mostrar_mensaje(Mensaje("Bob", "Alice", "PUBLICA", {"B": 19}))
        parametros.datos["p"] = 47
        self.assertEqual(escena.publicos_observados, {})
        escena._t = .6
        escena._dibujar()
        self.assertTrue(escena.canvas.find_withtag("paquete"))
        self.completar_animaciones()
        self.assertEqual(escena.publicos_observados, {"p": 23, "g": 5, "A": 8, "B": 19})
        self.assertFalse(escena.canvas.find_withtag("paquete"))

    def test_reiniciar_cancela_paquetes_y_desbloquea_los_controles(self):
        self.v.escena.establecer_animaciones(True)
        self.parametros()
        self.assertTrue(self.v.escena.en_animacion)
        self.assertEqual(self.v.t_alice.entrada_priv.cget("state"), "disabled")
        self.v.reiniciar()
        self.app.update()
        self.assertIsNone(self.v.escena._after_id)
        self.assertFalse(self.v.escena.en_animacion)
        self.assertEqual(self.v.escena.publicos_observados, {})
        self.assertEqual(self.v.eve_sabe, {})
        self.assertEqual(self.v.t_alice.entrada_priv.cget("state"), "normal")
        self.assertIsNone(self.v.alice.p)

    def test_desactivar_animaciones_termina_la_cola_sin_perder_mensajes(self):
        self.v.escena.establecer_animaciones(True)
        self.parametros()
        self.v.escena.establecer_animaciones(False)
        self.assertFalse(self.v.escena.en_animacion)
        self.assertIsNone(self.v.escena._after_id)
        self.assertEqual(self.v.escena.publicos_observados, {"p": 23, "g": 5})
        self.assertEqual(self.v.t_alice.btn_publica.cget("state"), "normal")

    def test_numeros_grandes_se_conservan_completos_en_consola_y_al_copiar(self):
        self.parametros(p=2**127-1, g=3)
        self.calcular(a=110, b=211)
        self.v.t_alice.btn_enviar.invoke()
        self.v.t_bob.btn_enviar.invoke()
        self.v.t_alice.btn_secreto.invoke()
        self.v.t_bob.btn_secreto.invoke()
        self.assertEqual(self.v.alice.secreto, self.v.bob.secreto)
        publica = self.v.alice.publica
        self.assertIn(str(publica), self.v.consola.get("1.0", "end"))
        self.assertIn("…", self.v.t_alice.campo_pub._lbl.cget("text"))
        campo = self.v.t_alice.campo_pub
        with patch.object(campo, "clipboard_clear"), patch.object(campo, "clipboard_append") as copiar:
            campo._copiar()
            copiar.assert_called_once_with(str(publica))
        self.assertEqual(self.v.escena.publicos_observados["A"], publica)

    def test_parametros_invalidos_no_borran_la_sesion_ya_publicada(self):
        self.parametros()
        self.v.entrada_p.delete(0, "end")
        self.v.entrada_p.insert(0, "21")
        self.v._publicar_parametros()
        self.assertEqual(self.v.alice.p, 23)
        self.assertEqual(self.v.escena.publicos_observados, {"p": 23, "g": 5})
        self.assertIn("no es primo", self.v.lbl_param.cget("text"))

    def test_reiniciar_descarta_una_generacion_que_termina_tarde(self):
        with patch("gui.vistas.modo_local.tema.correr_en_hilo") as trabajo:
            self.v._generar_parametros()
        listo = trabajo.call_args.args[2]
        self.v.reiniciar()
        listo((47, 5, []))
        self.assertEqual(self.v.entrada_p.get(), "")
        self.assertEqual(self.v.btn_generar.cget("state"), "normal")
        self.assertIsNone(self.v.alice.p)


if __name__ == "__main__":
    unittest.main()
