import copy
import json
import tempfile
import unittest
from uuid import uuid4

from core.cifrado import ErrorCifrado
from protocolo.conversacion import Conversacion
from servidor.salas import Conexion, ErrorSala, Salas
from transporte.canal import CanalArchivo, Mensaje


class ConversacionTests(unittest.TestCase):
    def setUp(self):
        self.c = Conversacion()
        self.id = uuid4().hex
        self.publicos = {"p": 23, "g": 5, "A": 8, "B": 19}
        self.c.actualizar(self.publicos, self.id)

    def test_recibido_pendiente_descifrado_por_receptor_y_eve_por_separado(self):
        m = self.c.preparar("Alice", "¡Hola Bob! 🔑\nSegunda línea", 2)
        r = self.c.registrar(m, "¡Hola Bob! 🔑\nSegunda línea")
        self.c.descifrar_pendientes({"Alice": 2})
        self.assertIsNone(r.lecturas["Bob"])
        self.assertIsNone(r.lecturas["Eve"])
        self.c.descifrar_pendientes({"Bob": 2})
        self.assertEqual(r.lecturas["Bob"], r.texto_propio)
        self.assertIsNone(r.lecturas["Eve"])
        self.c.descifrar_pendientes({"Bob": 2}, 3)
        self.assertIsInstance(r.lecturas["Eve"], ErrorCifrado)
        self.c.descifrar_pendientes({"Bob": 2}, 2)
        self.assertEqual(r.lecturas["Eve"], r.texto_propio)
        self.c.descifrar_pendientes({})
        self.assertIsNone(r.lecturas["Bob"])
        self.assertIsNone(r.lecturas["Eve"])

    def test_el_contexto_autentica_id_direccion_publicos_y_sesion(self):
        original = self.c.preparar("Alice", "Reservado", 2)
        variantes = []
        cambio_id = copy.deepcopy(original)
        cambio_id.datos["id"] = uuid4().hex
        variantes.append((self.publicos, self.id, cambio_id))
        cambio_direccion = copy.deepcopy(original)
        cambio_direccion.remitente, cambio_direccion.destinatario = "Bob", "Alice"
        variantes.append((self.publicos, self.id, cambio_direccion))
        cambio_sesion = copy.deepcopy(original)
        cambio_sesion.intercambio = uuid4().hex
        variantes.append((self.publicos, cambio_sesion.intercambio, cambio_sesion))
        variantes.append(({**self.publicos, "A": 9}, self.id, original))
        for publicos, intercambio, m in variantes:
            with self.subTest(m=m):
                c = Conversacion()
                c.actualizar(publicos, intercambio)
                r = c.registrar(m)
                c.descifrar_pendientes({m.destinatario: 2})
                self.assertIsInstance(r.lecturas[m.destinatario], ErrorCifrado)

    def test_actualizar_k_no_descifra_y_cada_accion_abre_un_solo_mensaje(self):
        primero = self.c.registrar(self.c.preparar("Alice", "Primero", 2))
        segundo = self.c.registrar(self.c.preparar("Alice", "Segundo", 2))
        self.assertEqual(self.c.actualizar_claves({"Bob": 2}), [])
        self.assertEqual(self.c.pendientes("Bob"), [primero, segundo])
        self.assertIsNone(primero.lecturas["Bob"])
        self.c.descifrar(primero.mensaje.datos["id"], "Bob", 2)
        self.assertEqual(primero.lecturas["Bob"], "Primero")
        self.assertIsNone(segundo.lecturas["Bob"])
        self.assertEqual(self.c.pendientes("Bob"), [segundo])
        self.assertEqual(self.c.descifrar(primero.mensaje.datos["id"], "Bob", 2), [])
        self.c.actualizar_claves({"Bob": 2}, 2)
        self.assertEqual(segundo.lecturas["Eve"], "Segundo")
        self.assertIsNone(segundo.lecturas["Bob"])

    def test_descifrado_manual_valida_destinatario_y_k_y_permite_corregirla(self):
        r = self.c.registrar(self.c.preparar("Alice", "Solo para Bob", 2))
        identificador = r.mensaje.datos["id"]
        for rol, clave in (("Alice", 2), ("Bob", None), ("Bob", True)):
            with self.subTest(rol=rol, clave=clave), self.assertRaises(ValueError):
                self.c.descifrar(identificador, rol, clave)
        self.c.actualizar_claves({"Bob": 3})
        self.c.descifrar(identificador, "Bob", 3)
        self.assertIsInstance(r.lecturas["Bob"], ErrorCifrado)
        self.assertEqual(self.c.pendientes("Bob"), [])
        self.c.actualizar_claves({"Bob": 2})
        self.assertEqual(self.c.pendientes("Bob"), [r])
        self.c.descifrar(identificador, "Bob", 2)
        self.assertEqual(r.lecturas["Bob"], "Solo para Bob")

    def test_repeticiones_no_duplican_y_cambios_de_datos_limpian_el_historial(self):
        m = self.c.preparar("Bob", "Respuesta", 2)
        self.c.registrar(m)
        self.c.registrar(Mensaje.desde_texto(m.a_texto()))
        self.assertEqual(len(self.c.registros), 1)
        otro = self.c.preparar("Bob", "Otro", 2)
        otro.datos["id"] = m.datos["id"]
        with self.assertRaises(ValueError):
            self.c.registrar(otro)
        with self.assertRaises(ValueError):
            self.c.registrar(Mensaje("Bob", "Alice", "CIFRADO", m.datos, uuid4().hex))
        self.c.actualizar({**self.publicos, "B": 20}, self.id)
        self.assertEqual(self.c.registros, [])

    def test_archivos_solo_transportan_el_sobre_y_conservan_unicode_al_descifrar(self):
        with tempfile.TemporaryDirectory() as carpeta:
            canal = CanalArchivo(carpeta)
            for rol in ("Alice", "Bob"):
                m = self.c.preparar(rol, "Texto privado: áéíóú 🔐", 2)
                canal.enviar(m)
                contenido = next(canal.carpeta.glob("*.txt")).read_text(encoding="utf-8")
                self.assertNotIn("Texto privado", contenido)
                recibido = canal.recibir(m.destinatario)
                r = self.c.registrar(recibido)
                self.c.descifrar_pendientes({m.destinatario: 2})
                self.assertEqual(r.lecturas[m.destinatario], "Texto privado: áéíóú 🔐")
                canal.confirmar(recibido)

    def test_formato_rechaza_secretos_y_sobres_incompletos(self):
        m = self.c.preparar("Alice", "hola", 2)
        self.assertEqual(set(m.datos), {"id", "sobre"})
        for datos in ({**m.datos, "K": 2}, {**m.datos, "id": "abc"},
                      {**m.datos, "sobre": "{}"}, {**m.datos, "sobre": 23},
                      {**m.datos, "sobre": json.dumps(json.loads(m.datos["sobre"]), indent=2)}):
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                Mensaje("Alice", "Bob", "CIFRADO", datos, self.id).validar()


class ServidorCifradoTests(unittest.TestCase):
    def setUp(self):
        self.s = Salas()
        self.ea, self.eb = [], []
        self.a, self.b = Conexion(emitir=self.ea.append), Conexion(emitir=self.eb.append)
        self.s.ejecutar(self.a, {"accion": "crear"})
        self.s.ejecutar(self.b, {"accion": "unir", "sala": self.a.sala})
        self.s.ejecutar(self.a, {"accion": "elegir", "rol": "Alice"})
        self.s.ejecutar(self.b, {"accion": "elegir", "rol": "Bob"})
        self.sala = self.s.salas[self.a.sala]
        self.c = Conversacion()
        self.c.actualizar({"p": 23, "g": 5, "A": 8, "B": 19}, self.sala.partida)

    def publicar(self, c, tipo, datos):
        self.s.ejecutar(c, {"accion": "publicar", "partida": self.sala.partida, "tipo": tipo, "datos": datos})

    def test_reenvia_solo_ciphertext_rechaza_replay_y_exige_publicas(self):
        m = self.c.preparar("Alice", "Secreto para Bob", 2)
        with self.assertRaises(ErrorSala):
            self.publicar(self.a, "CIFRADO", m.datos)
        self.publicar(self.a, "PARAMETROS", {"p": "23", "g": "5"})
        self.publicar(self.a, "PUBLICA", {"A": "8"})
        self.publicar(self.b, "PUBLICA", {"B": "19"})
        self.publicar(self.a, "CIFRADO", m.datos)
        self.assertEqual(self.ea[-1], self.eb[-1])
        self.assertEqual(self.ea[-1]["datos"], m.datos)
        self.assertNotIn("Secreto para Bob", json.dumps(self.ea[-1]))
        self.assertEqual(self.sala.publicos, self.c.publicos)
        with self.assertRaises(ErrorSala):
            self.publicar(self.a, "CIFRADO", m.datos)
        with self.assertRaises(ErrorSala):
            self.publicar(self.a, "CIFRADO", {**m.datos, "K": "2"})
        self.s.desconectar(self.b)
        self.assertEqual(self.sala.mensajes, set())


if __name__ == "__main__":
    unittest.main()
