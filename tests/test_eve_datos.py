"""Importación de datos públicos y ataque desde las vistas reales."""
import tempfile
import time
import unittest

from gui.app import App
from transporte.canal import CanalArchivo, Mensaje


class DatosEveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App()
        cls.app.withdraw()

    @classmethod
    def tearDownClass(cls):
        # Tk comparte la cola de eventos del hilo entre las raíces de la suite.
        for identificador in cls.app.tk.call("after", "info"):
            # Cancelar el evento; cada widget eliminará su propio comando al destruirse.
            cls.app.tk.call("after", "cancel", identificador)
        cls.app.destroy()

    def setUp(self):
        self.local = self.app.vistas["local"]
        self.app.vistas["red"].mostrar("Archivos .txt")
        self.red = self.app.vistas["red"].archivos
        self.eve = self.app.vistas["eve"]
        self.local.reiniciar()
        self.red._cambiar_rol("Alice")
        self.red.entrada_carpeta.delete(0, "end")
        self.red.entrada_sesion.delete(0, "end")
        self.red.entrada_sesion.insert(0, "demo")
        self.eve._set_buscando(False)
        self.eve.cargar({})
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.red._desconectar(avisar=False)
        self.tmp.cleanup()

    def preparar_local(self, enviar=True):
        self.local.entrada_p.insert(0, "23")
        self.local.entrada_g.insert(0, "5")
        self.local._publicar_parametros()
        self.local.alice.establecer_privada(6)
        self.local.alice.calcular_publica()
        if enviar:
            self.local._enviar(self.local.alice)

    def conectar_red(self, rol="Alice"):
        self.red._cambiar_rol(rol)
        self.red.entrada_carpeta.insert(0, self.tmp.name)
        self.red._conectar()
        self.assertIsNotNone(self.red.canal, self.red.lbl_estado.cget("text"))

    def valores(self):
        return {k: entrada.get() for k, entrada in self.eve.entradas.items()}

    def test_local_importa_solo_datos_que_pasaron_por_el_canal(self):
        self.preparar_local(enviar=False)
        self.eve.btn_local.invoke()
        self.assertEqual(self.valores(), {"p": "23", "g": "5", "A": ""})
        self.assertIn("faltan A", self.eve.lbl_origen.cget("text"))
        self.local._enviar(self.local.alice)
        self.local.eve_sabe.update({"privada": 6, "secreto": 2})
        self.eve.btn_local.invoke()
        self.assertEqual(self.valores(), {"p": "23", "g": "5", "A": "8"})
        self.assertEqual(self.app._datos_para_eve("local"), {"p": 23, "g": 5, "A": 8})

    def test_cambiar_a_origen_incompleto_limpia_la_publica_anterior(self):
        self.preparar_local()
        self.eve.btn_local.invoke()
        self.conectar_red()
        self.red._poner_parametros(47, 5)
        self.red._publicar_params_red()
        self.red.yo.establecer_privada(6)
        self.red.yo.calcular_publica()  # Todavía no enviada.
        self.eve.btn_red.invoke()
        self.assertEqual(self.valores(), {"p": "47", "g": "5", "A": ""})
        self.assertIn("Modo red: faltan A", self.eve.lbl_origen.cget("text"))

    def test_red_alice_importa_sin_consumir_la_cola_y_conserva_datos_confirmados(self):
        self.conectar_red()
        self.red._poner_parametros(23, 5)
        self.red._publicar_params_red()
        self.red.yo.establecer_privada(6)
        self.red.yo.calcular_publica()
        self.red._enviar(self.red.yo)
        archivos = list(self.red.canal.carpeta.glob("*.txt"))
        self.assertEqual(len(archivos), 2)
        self.eve.btn_red.invoke()
        self.assertEqual(list(self.red.canal.carpeta.glob("*.txt")), archivos)
        self.assertEqual(self.valores(), {"p": "23", "g": "5", "A": "8"})
        bob = CanalArchivo(self.tmp.name)
        for _ in range(2):
            mensaje = bob.recibir("Bob")
            bob.confirmar(mensaje)
        self.assertEqual(list(self.red.canal.carpeta.glob("*.txt")), [])
        self.eve.btn_red.invoke()
        self.assertEqual(self.valores()["A"], "8")
        self.assertEqual(set(self.app._datos_para_eve("red")), {"p", "g", "A"})

    def test_red_bob_puede_importar_la_publica_que_recibio(self):
        self.conectar_red("Bob")
        alice = CanalArchivo(self.tmp.name)
        alice.enviar(Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5}))
        alice.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))
        self.red._verificar_mensajes()
        self.eve.btn_red.invoke()
        self.assertEqual(self.valores(), {"p": "23", "g": "5", "A": "8"})

    def test_origen_vacio_y_desconexion_no_reutilizan_datos_anteriores(self):
        self.preparar_local()
        self.eve.btn_local.invoke()
        self.local.reiniciar()
        self.eve.btn_local.invoke()
        self.assertEqual(self.valores(), {"p": "", "g": "", "A": ""})
        self.conectar_red()
        self.red._poner_parametros(23, 5)
        self.red._publicar_params_red()
        self.eve.btn_red.invoke()
        self.assertEqual(self.valores()["p"], "23")
        self.red._desconectar()
        self.eve.btn_red.invoke()
        self.assertEqual(self.valores(), {"p": "", "g": "", "A": ""})

    def test_datos_importados_permiten_atacar_y_se_bloquean_cambios_durante_busqueda(self):
        self.preparar_local()
        self.eve.btn_local.invoke()
        self.eve.sel_max.set("10 mil")
        self.eve.btn.invoke()
        self.assertEqual(self.eve.btn_red.cget("state"), "disabled")
        self.assertEqual(self.eve.entradas["A"].cget("state"), "disabled")
        self.eve.cargar({"p": 47, "g": 5, "A": 9}, origen="Modo red")
        self.assertEqual(self.valores()["p"], "23")
        limite = time.monotonic() + 3
        while self.eve._buscando and time.monotonic() < limite:
            self.app.update()
            time.sleep(0.01)
        self.assertFalse(self.eve._buscando)
        self.assertIn("a = 6", self.eve.resultado.get("1.0", "end"))
        self.assertEqual(self.eve.btn_red.cget("state"), "normal")

    def test_atajo_existente_del_modo_local_sigue_abriendo_eve(self):
        self.preparar_local()
        self.app._abrir_eve(self.local.eve_sabe)
        self.assertEqual(self.valores(), {"p": "23", "g": "5", "A": "8"})
        self.assertEqual(self.eve.winfo_manager(), "grid")


if __name__ == "__main__":
    unittest.main()
