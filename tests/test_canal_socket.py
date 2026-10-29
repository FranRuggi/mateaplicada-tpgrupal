"""Canal TCP directo: conexión, orden, mensajes partidos, validación y cierre."""
import socket
import time
import unittest

from protocolo.sesion import Participante
from transporte.canal import CanalSocket, ErrorCanal, Mensaje


def esperar(condicion, segundos=5):
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.02)
    return False


def recibir(canal, destinatario):
    """Esperar el próximo mensaje y confirmarlo, como hace el sondeo de la GUI."""
    mensajes = []
    esperar(lambda: mensajes.append(canal.recibir(destinatario)) or mensajes[-1] is not None)
    canal.confirmar(mensajes[-1])
    return mensajes[-1]


class CanalSocketTests(unittest.TestCase):
    def setUp(self):
        # Puerto 0: el sistema elige uno libre.
        self.bob = CanalSocket("", 0, es_servidor=True)
        self.addCleanup(self.bob.cerrar)

    def conectar_alice(self):
        alice = CanalSocket("127.0.0.1", self.bob.puerto, es_servidor=False)
        self.addCleanup(alice.cerrar)
        self.assertTrue(esperar(lambda: alice.conectado and self.bob.conectado))
        return alice

    def test_intercambio_diffie_hellman_completo(self):
        alice_canal = self.conectar_alice()
        alice, bob = Participante("Alice"), Participante("Bob")

        alice.establecer_parametros(23, 5)
        alice_canal.enviar(Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5}))
        datos = recibir(self.bob, "Bob").datos
        bob.establecer_parametros(datos["p"], datos["g"])

        alice.establecer_privada(6)
        bob.establecer_privada(15)
        alice_canal.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": alice.calcular_publica()[0]}))
        self.bob.enviar(Mensaje("Bob", "Alice", "PUBLICA", {"B": bob.calcular_publica()[0]}))
        bob.recibir_publica(recibir(self.bob, "Bob").datos["A"])
        alice.recibir_publica(recibir(alice_canal, "Alice").datos["B"])

        self.assertEqual(alice.derivar_secreto()[0], 2)
        self.assertEqual(bob.derivar_secreto()[0], 2)

    def test_alice_reintenta_hasta_que_bob_escucha(self):
        libre = socket.create_server(("127.0.0.1", 0))
        puerto = libre.getsockname()[1]
        libre.close()
        alice = CanalSocket("127.0.0.1", puerto, es_servidor=False)
        self.addCleanup(alice.cerrar)
        time.sleep(1.2)
        self.assertFalse(alice.conectado)
        with self.assertRaises(ErrorCanal):
            alice.enviar(Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5}))
        bob = CanalSocket("", puerto, es_servidor=True)
        self.addCleanup(bob.cerrar)
        self.assertTrue(esperar(lambda: alice.conectado and bob.conectado))

    def test_varios_mensajes_llegan_en_orden_aunque_tcp_los_parta(self):
        cliente = socket.create_connection(("127.0.0.1", self.bob.puerto))
        self.addCleanup(cliente.close)
        texto = (Mensaje("Alice", "Bob", "PARAMETROS", {"p": 23, "g": 5}).a_texto() + "\n"
                 + Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}).a_texto() + "\n").encode()
        for i in range(0, len(texto), 7):
            cliente.sendall(texto[i:i + 7])
            time.sleep(0.01)
        self.assertEqual(recibir(self.bob, "Bob").tipo, "PARAMETROS")
        self.assertEqual(recibir(self.bob, "Bob").datos, {"A": 8})

    def test_mensaje_invalido_se_descarta_sin_cortar_la_conexion(self):
        cliente = socket.create_connection(("127.0.0.1", self.bob.puerto))
        self.addCleanup(cliente.close)
        cliente.sendall(b"de=Eve\npara=Bob\ntipo=PUBLICA\nA=1\n\n")
        cliente.sendall(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}).a_texto().encode() + b"\n")
        with self.assertRaisesRegex(ErrorCanal, "inválido"):
            esperar(lambda: self.bob.recibir("Bob") is not None)
        self.assertTrue(self.bob.conectado)
        self.assertEqual(recibir(self.bob, "Bob").datos, {"A": 8})

    def test_posponer_conserva_el_mensaje_primero(self):
        alice = self.conectar_alice()
        alice.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))
        self.assertTrue(esperar(lambda: self.bob.recibir("Bob") is not None))
        mensaje = self.bob.recibir("Bob")
        self.bob.posponer(mensaje)
        self.assertIs(self.bob.recibir("Bob"), mensaje)

    def test_desconexion_del_otro_se_informa(self):
        alice = self.conectar_alice()
        alice.cerrar()
        self.assertTrue(esperar(lambda: not self.bob.conectado))
        with self.assertRaisesRegex(ErrorCanal, "Alice se desconectó"):
            self.bob.recibir("Bob")

    def test_cerrar_el_canal_actualiza_el_estado_local_y_es_repetible(self):
        alice = self.conectar_alice()
        alice.cerrar()
        self.assertFalse(alice.conectado)
        self.assertEqual(alice.estado(), "Desconectado")
        alice.cerrar()
        with self.assertRaises(ErrorCanal):
            alice.enviar(Mensaje("Alice", "Bob", "PUBLICA", {"A": 8}))

    def test_validaciones_al_crear(self):
        with self.assertRaises(ValueError):
            CanalSocket("", 5000, es_servidor=False)
        with self.assertRaises(ValueError):
            CanalSocket("127.0.0.1", 70000, es_servidor=False)
        with self.assertRaises(ErrorCanal):
            CanalSocket("", self.bob.puerto, es_servidor=True)


if __name__ == "__main__":
    unittest.main()
