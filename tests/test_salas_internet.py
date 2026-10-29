import queue
import time
import unittest
from unittest.mock import patch

from core import aritmetica
from servidor_prueba import ServidorPrueba
from transporte.internet import ClienteSalas, url_websocket
from websockets.sync.client import connect as conectar_real


class SalasInternetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = ServidorPrueba().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.__exit__()

    def setUp(self):
        self.clientes = []

    def tearDown(self):
        for c in self.clientes:
            c.cerrar()
        for c in self.clientes:
            c._hilo.join(timeout=3)

    def cliente(self):
        c = ClienteSalas(self.servidor.url)
        self.clientes.append(c)
        c.conectar()
        self.esperar(c, lambda e: e["evento"] == "bienvenida")
        return c

    def esperar(self, c, condicion):
        limite = time.monotonic()+5
        vistos = []
        while time.monotonic() < limite:
            try:
                e = c.eventos.get(timeout=.1)
            except queue.Empty:
                continue
            vistos.append(e)
            if condicion(e):
                return e
        self.fail(f"No llegó el evento esperado. Eventos: {vistos}")

    def sala(self):
        a, b = self.cliente(), self.cliente()
        a.enviar("crear")
        estado = self.esperar(a, lambda e: e["evento"] == "estado")
        b.enviar("unir", sala=estado["sala"])
        self.esperar(b, lambda e: e["evento"] == "estado")
        a.enviar("elegir", rol="Alice")
        b.enviar("elegir", rol="Bob")
        ea = self.esperar(a, lambda e: e["evento"] == "estado" and e.get("partida"))
        eb = self.esperar(b, lambda e: e["evento"] == "estado" and e.get("partida"))
        self.assertEqual(ea["partida"], eb["partida"])
        return a, b, ea

    def test_dos_elecciones_simultaneas_reservan_alice_una_sola_vez(self):
        a, b = self.cliente(), self.cliente()
        a.enviar("crear")
        codigo = self.esperar(a, lambda e: e["evento"] == "estado")["sala"]
        b.enviar("unir", sala=codigo)
        self.esperar(b, lambda e: e["evento"] == "estado")
        a.enviar("elegir", rol="Alice")
        b.enviar("elegir", rol="Alice")
        estados = []
        for c in (a, b):
            c.enviar("estado")
            estados.append(self.esperar(c, lambda e: e["evento"] == "estado" and e["roles"]["Alice"]))
        ganador = a if estados[0]["rol"] == "Alice" else b
        perdedor = b if ganador is a else a
        # Consultar después de que ambos comandos se procesaron.
        perdedor.enviar("elegir", rol="Bob")
        listo = self.esperar(perdedor, lambda e: e["evento"] == "estado" and e.get("partida"))
        self.assertEqual(listo["rol"], "Bob")
        self.assertTrue(all(listo["roles"].values()))

    def test_solo_dos_personas_pueden_entrar(self):
        _, _, estado = self.sala()
        tercero = self.cliente()
        tercero.enviar("unir", sala=estado["sala"])
        error = self.esperar(tercero, lambda e: e["evento"] == "error")
        self.assertIn("dos participantes", error["mensaje"])

    def test_intercambio_real_de_enteros_grandes_y_solo_campos_publicos(self):
        a, b, estado = self.sala()
        p, g = 2**127-1, 3
        A = aritmetica.mod_pow(g, 110, p)[0]
        B = aritmetica.mod_pow(g, 211, p)[0]
        for cliente, tipo, datos in ((a, "PARAMETROS", {"p": p, "g": g}),
                                     (a, "PUBLICA", {"A": A}), (b, "PUBLICA", {"B": B})):
            cliente.enviar("publicar", partida=estado["partida"], tipo=tipo,
                            datos={k: str(v) for k, v in datos.items()})
            for receptor in (a, b):
                evento = self.esperar(receptor, lambda e: e["evento"] == "mensaje")
                self.assertEqual({k: int(v) for k, v in evento["datos"].items()}, datos)
                self.assertFalse({"a", "b", "privada", "secreto", "K"} & evento["datos"].keys())
        self.assertEqual(aritmetica.mod_pow(B, 110, p)[0], aritmetica.mod_pow(A, 211, p)[0])

    def test_el_servidor_rechaza_suplantacion_y_secretos(self):
        a, b, estado = self.sala()
        b.enviar("publicar", partida=estado["partida"], tipo="PARAMETROS", datos={"p": "23", "g": "5"})
        self.assertIn("Solo Alice", self.esperar(b, lambda e: e["evento"] == "error")["mensaje"])
        a.enviar("publicar", partida=estado["partida"], tipo="PUBLICA", datos={"A": "8", "a": "6"})
        self.assertIn("Solo pueden", self.esperar(a, lambda e: e["evento"] == "error")["mensaje"])
        a.enviar("publicar", partida=estado["partida"], tipo="PUBLICA", datos={"A": "8"}, remitente="Bob")
        self.assertIn("campos no permitidos", self.esperar(a, lambda e: e["evento"] == "error")["mensaje"])

    def test_salir_libera_el_rol_y_la_partida_nueva_rechaza_envios_viejos(self):
        a, b, estado = self.sala()
        b.cerrar()
        self.esperar(a, lambda e: e["evento"] == "estado" and not e.get("partida"))
        nuevo = self.cliente()
        nuevo.enviar("unir", sala=estado["sala"])
        self.esperar(nuevo, lambda e: e["evento"] == "estado")
        nuevo.enviar("elegir", rol="Bob")
        siguiente = self.esperar(a, lambda e: e["evento"] == "estado" and e.get("partida"))
        self.assertNotEqual(estado["partida"], siguiente["partida"])
        a.enviar("publicar", partida=estado["partida"], tipo="PARAMETROS", datos={"p": "23", "g": "5"})
        self.assertIn("terminó", self.esperar(a, lambda e: e["evento"] == "error")["mensaje"])

    def test_validacion_de_url_no_expone_credenciales_en_la_conexion(self):
        self.assertEqual(url_websocket("https://ejemplo.onrender.com"), "wss://ejemplo.onrender.com/ws")
        with self.assertRaises(ValueError):
            url_websocket("https://usuario:clave@ejemplo.com")

    def test_un_arranque_transitorio_se_reintenta_sin_perder_la_conexion(self):
        c = ClienteSalas(self.servidor.url)
        self.clientes.append(c)
        intentos = []

        def arranque(url, **opciones):
            intentos.append(True)
            if len(intentos) == 1:
                raise OSError("Servidor arrancando")
            return conectar_real(url, **opciones)

        with patch("transporte.internet.connect", side_effect=arranque):
            c.conectar()
            self.esperar(c, lambda e: e["evento"] == "conectando")
            self.esperar(c, lambda e: e["evento"] == "bienvenida")
        self.assertEqual(len(intentos), 2)

    def test_salir_cancela_la_espera_de_arranque(self):
        c = ClienteSalas(self.servidor.url)
        self.clientes.append(c)
        with patch("transporte.internet.connect", side_effect=OSError("No disponible")):
            c.conectar()
            self.esperar(c, lambda e: e["evento"] == "conectando")
            c.cerrar()
            c._hilo.join(timeout=1)
        self.assertFalse(c._hilo.is_alive())

    def test_un_certificado_invalido_no_se_ignora_ni_se_reintenta(self):
        import ssl
        c = ClienteSalas(self.servidor.url)
        self.clientes.append(c)
        with patch("transporte.internet.connect", side_effect=ssl.SSLCertVerificationError("Certificado inválido")) as llamada:
            c.conectar()
            self.esperar(c, lambda e: e["evento"] == "desconectado")
        self.assertEqual(llamada.call_count, 1)
