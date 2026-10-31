"""Mover o ampliar el registro conserva la sesión y sus widgets activos."""
import time
import unittest

from gui.app import App
from gui.registro import AreaConRegistro


class RegistroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App()
        cls.app.withdraw()
        cls.errores = []
        cls.app.report_callback_exception = lambda *error: cls.errores.append(error)

    @classmethod
    def tearDownClass(cls):
        for identificador in cls.app.tk.call("after", "info"):
            cls.app.tk.call("after", "cancel", identificador)
        cls.app.destroy()

    def setUp(self):
        self.v = self.app.vistas["local"]
        self.v.reiniciar()
        self.v.escena.establecer_animaciones(False)
        self.v.colocar_registro("Abajo")
        self.errores.clear()

    def tearDown(self):
        self.v.reiniciar()
        self.assertEqual(self.errores, [])

    def preparar(self):
        self.v.entrada_p.insert(0, "23")
        self.v.entrada_g.insert(0, "5")
        self.v._publicar_parametros()
        for tarjeta, valor in ((self.v.t_alice, 6), (self.v.t_bob, 15)):
            tarjeta.entrada_priv.insert(0, str(valor))
            tarjeta.btn_publica.invoke()

    def test_al_mover_se_conservan_historial_detalle_y_pestana_seleccionada(self):
        self.preparar()
        self.v.registro.set("Paso a paso")
        consola, pasos = self.v.consola, self.v.pasos.caja
        historial, detalle = consola.get("1.0", "end"), pasos.get("1.0", "end")
        for ubicacion in ("Derecha", "Abajo", "Derecha"):
            self.v.colocar_registro(ubicacion)
            self.v.ampliar_registro()
            self.v.ampliar_registro()
            self.app.update()
            self.assertIs(self.v.consola, consola)
            self.assertIs(self.v.pasos.caja, pasos)
            self.assertEqual(consola.get("1.0", "end"), historial)
            self.assertEqual(pasos.get("1.0", "end"), detalle)
            self.assertEqual(self.v.registro.get(), "Paso a paso")

    def test_el_intercambio_sigue_funcionando_con_la_consola_lateral(self):
        self.preparar()
        self.v.colocar_registro("Derecha")
        self.v.t_alice.btn_enviar.invoke()
        self.v.t_bob.btn_enviar.invoke()
        self.v.t_alice.btn_secreto.invoke()
        self.v.t_bob.btn_secreto.invoke()
        self.assertEqual((self.v.alice.secreto, self.v.bob.secreto), (2, 2))
        self.assertIn("A = 8", self.v.consola.get("1.0", "end"))
        self.assertIn("B = 19", self.v.consola.get("1.0", "end"))
        self.assertIn("Bob: K", self.v.pasos.caja.get("1.0", "end"))

    def test_cambiar_ubicacion_durante_el_ataque_no_lo_interrumpe(self):
        self.preparar()
        self.v.t_alice.btn_enviar.invoke()
        self.v.t_bob.btn_enviar.invoke()
        ataque = self.v.ataque_eve
        ataque.btn.invoke()
        self.v.colocar_registro("Derecha")
        limite = time.monotonic()+3
        while ataque._buscando and time.monotonic() < limite:
            self.app.update()
            time.sleep(.01)
        self.assertFalse(ataque._buscando)
        self.assertEqual(ataque._resultado.exponente, 6)
        self.assertEqual(ataque._secreto, 2)
        self.assertIn("Eve encontró a = 6", self.v.consola.get("1.0", "end"))

    def test_ajuste_oculto_o_sin_separador_espera_a_que_el_panel_este_listo(self):
        area = AreaConRegistro(self.app)
        try:
            self.assertFalse(area.division.winfo_ismapped())
            area._aplicar_tamano()
            area.division.forget(area.panel_registro)
            area._aplicar_tamano()
            self.app.update()
            self.assertEqual(self.errores, [])
            area.division.add(area.panel_registro, stretch="never")
            area.grid(row=0, column=2, sticky="nsew")
            self.app.deiconify()
            self.app.update()
            area.colocar_registro("Derecha")
            self.app.update()
            self.assertEqual(len(area.division.panes()), 2)
            area.division.sash_coord(0)
            self.assertEqual(self.errores, [])
        finally:
            area.destroy()
            self.app.withdraw()


if __name__ == "__main__":
    unittest.main()
