"""Derivación, autenticación, formato público y un intercambio DH con Eve."""
import base64
from dataclasses import replace
import json
import unittest

from core.aritmetica import log_discreto_fuerza_bruta, potencia_modular
from core.clave_simetrica import derivar_clave
from core.cifrado import ErrorAutenticacion, ErrorCifrado, cifrar_bytes, descifrar_bytes
from protocolo.mensajes_cifrados import (
    ErrorMensajeCifrado, MAX_SOBRE_BYTES, MAX_TEXTO_BYTES, MensajeCifrado,
    cifrar_mensaje, descifrar_mensaje,
)
from protocolo.sesion import Participante


class DerivacionClaveTests(unittest.TestCase):
    def test_vector_rfc5869_sha256_caso_1(self):
        # RFC 5869, apéndice A.1: los primeros 32 bytes del OKM de 42 bytes.
        # https://www.rfc-editor.org/rfc/rfc5869#appendix-A.1
        secreto = int.from_bytes(b"\x0b" * 22, "big")
        sal = bytes.fromhex("000102030405060708090a0b0c")
        contexto = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
        esperado = bytes.fromhex(
            "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf")
        self.assertEqual(derivar_clave(secreto, sal, contexto=contexto), esperado)

    def test_mismos_datos_reproducen_la_clave_y_cada_entrada_la_distingue(self):
        clave = derivar_clave(2, b"s" * 32, contexto=b"mensajes")
        self.assertEqual(len(clave), 32)
        self.assertEqual(derivar_clave(2, b"s" * 32, contexto=b"mensajes"), clave)
        self.assertNotEqual(derivar_clave(3, b"s" * 32, contexto=b"mensajes"), clave)
        self.assertNotEqual(derivar_clave(2, b"t" * 32, contexto=b"mensajes"), clave)
        self.assertNotEqual(derivar_clave(2, b"s" * 32, contexto=b"otro uso"), clave)

    def test_admite_secretos_de_demostracion_y_enteros_grandes(self):
        for secreto in (1, 2, 2**255 + 17, 2**4096 - 1):
            with self.subTest(secreto_bits=secreto.bit_length()):
                self.assertEqual(len(derivar_clave(secreto, b"s" * 32)), 32)

    def test_rechaza_datos_invalidos_sin_convertirlos_silenciosamente(self):
        for secreto in (None, True, False, 0, -1, "2", 2.0, 2**4096):
            with self.subTest(secreto_tipo=type(secreto), secreto_bits=getattr(secreto, "bit_length", lambda: 0)()):
                with self.assertRaises(ValueError):
                    derivar_clave(secreto, b"s" * 32)
        for sal in (None, "sal", b"", b"s" * 65):
            with self.subTest(sal=sal), self.assertRaises(ValueError):
                derivar_clave(2, sal)
        for contexto in (None, "texto", b"x" * 4097):
            with self.subTest(contexto_tipo=type(contexto)), self.assertRaises(ValueError):
                derivar_clave(2, b"s" * 32, contexto=contexto)


class CifradoBytesTests(unittest.TestCase):
    def test_bytes_arbitrarios_y_datos_asociados_se_recuperan_exactos(self):
        datos, clave, nonce = bytes(range(256)), bytes(range(32)), bytes(range(12))
        cifrado = cifrar_bytes(datos, clave, nonce, datos_asociados=b"cabecera")
        self.assertEqual(len(cifrado), len(datos) + 16)
        self.assertEqual(descifrar_bytes(cifrado, clave, nonce, datos_asociados=b"cabecera"), datos)

    def test_clave_nonce_contexto_o_contenido_distintos_no_entregan_texto(self):
        clave, nonce = b"k" * 32, b"n" * 12
        cifrado = cifrar_bytes(b"secreto", clave, nonce, datos_asociados=b"sesion")
        casos = (
            (cifrado, b"j" * 32, nonce, b"sesion"),
            (cifrado, clave, b"m" * 12, b"sesion"),
            (cifrado, clave, nonce, b"otra sesion"),
            (cifrado[:-1] + bytes([cifrado[-1] ^ 1]), clave, nonce, b"sesion"),
            (b"", clave, nonce, b"sesion"),
        )
        for datos, key, iv, aad in casos:
            with self.subTest(longitud=len(datos)), self.assertRaises(ErrorAutenticacion):
                descifrar_bytes(datos, key, iv, datos_asociados=aad)

    def test_validacion_de_material_criptografico(self):
        for funcion in (cifrar_bytes, descifrar_bytes):
            for datos, clave, nonce, asociados in (
                ("texto", b"k" * 32, b"n" * 12, b""),
                (b"texto", b"k" * 16, b"n" * 12, b""),
                (b"texto", b"k" * 32, b"n" * 11, b""),
                (b"texto", b"k" * 32, b"n" * 12, "contexto"),
            ):
                with self.subTest(funcion=funcion.__name__), self.assertRaises(ErrorCifrado):
                    funcion(datos, clave, nonce, datos_asociados=asociados)


class MensajesCifradosTests(unittest.TestCase):
    def test_textos_utf8_vacios_multilinea_y_emojis_sobreviven_el_formato(self):
        for texto in ("", "Hola, Bob", "¿Cómo estás? ñ á 😀\nOtra línea\x00final"):
            with self.subTest(texto=texto):
                mensaje = cifrar_mensaje(texto, 2, contexto=b"sala:Alice->Bob")
                serializado = mensaje.a_texto()
                self.assertTrue(serializado.isascii())
                self.assertNotIn("\n", serializado)
                recibido = MensajeCifrado.desde_texto(serializado)
                self.assertEqual(recibido, mensaje)
                self.assertEqual(descifrar_mensaje(recibido, 2, contexto=b"sala:Alice->Bob"), texto)

    def test_un_mismo_texto_se_cifra_de_forma_diferente_en_cada_envio(self):
        primero, segundo = cifrar_mensaje("Hola", 2), cifrar_mensaje("Hola", 2)
        self.assertNotEqual(primero.sal, segundo.sal)
        self.assertNotEqual(primero.nonce, segundo.nonce)
        self.assertNotEqual(primero.texto_cifrado, segundo.texto_cifrado)
        for mensaje in (primero, segundo):
            self.assertEqual(descifrar_mensaje(mensaje, 2), "Hola")

    def test_el_sobre_no_transporta_claves_ni_texto_original(self):
        texto = "Este mensaje completo no debe circular en claro."
        serializado = cifrar_mensaje(texto, 2).a_texto()
        self.assertNotIn(texto, serializado)
        self.assertEqual(set(json.loads(serializado)),
                         {"version", "algoritmo", "sal", "nonce", "texto_cifrado"})

    def test_k_o_contexto_incorrectos_y_alteraciones_del_sobre_fallan(self):
        mensaje = cifrar_mensaje("Hola", 2, contexto=b"sala:Alice->Bob")
        for secreto, contexto in ((3, b"sala:Alice->Bob"), (2, b"otra:Alice->Bob"),
                                   (2, b"sala:Bob->Alice")):
            with self.subTest(secreto=secreto, contexto=contexto), self.assertRaises(ErrorAutenticacion):
                descifrar_mensaje(mensaje, secreto, contexto=contexto)
        for campo in ("sal", "nonce", "texto_cifrado"):
            dato = getattr(mensaje, campo)
            alterado = replace(mensaje, **{campo: bytes([dato[0] ^ 1]) + dato[1:]})
            recibido = MensajeCifrado.desde_texto(alterado.a_texto())
            with self.subTest(campo=campo), self.assertRaises(ErrorAutenticacion):
                descifrar_mensaje(recibido, 2, contexto=b"sala:Alice->Bob")

    def test_rechaza_json_invalido_campos_extra_repetidos_y_versiones_no_admitidas(self):
        valido = json.loads(cifrar_mensaje("Hola", 2).a_texto())
        entradas = ["{", "[]", "null", "1", '"texto"', "[" * 1100 + "]" * 1100,
                    '{"version":1,"version":1}', "x" * (MAX_SOBRE_BYTES + 1)]
        for version in (0, 2, True, 1.0, "1", None):
            entradas.append(json.dumps({**valido, "version": version}))
        entradas.extend((json.dumps({**valido, "algoritmo": "otro"}),
                         json.dumps({**valido, "K": 2}),
                         json.dumps({k: v for k, v in valido.items() if k != "sal"})))
        for entrada in entradas:
            with self.subTest(inicio=entrada[:60]), self.assertRaises(ErrorMensajeCifrado):
                MensajeCifrado.desde_texto(entrada)

    def test_rechaza_base64_y_tamanos_binarios_invalidos(self):
        valido = json.loads(cifrar_mensaje("Hola", 2).a_texto())
        for campo in ("sal", "nonce", "texto_cifrado"):
            for dato in (None, 123, "ñ", "@@@", "", " "+valido[campo], valido[campo]+"="):
                with self.subTest(campo=campo, dato=dato), self.assertRaises(ErrorMensajeCifrado):
                    MensajeCifrado.desde_texto(json.dumps({**valido, campo: dato}))
        for campo, dato in (("sal", b"s" * 31), ("nonce", b"n" * 11),
                            ("texto_cifrado", b"t" * 15),
                            ("texto_cifrado", b"t" * (MAX_TEXTO_BYTES + 17))):
            with self.subTest(campo=campo), self.assertRaises(ErrorMensajeCifrado):
                MensajeCifrado.desde_texto(json.dumps({
                    **valido, campo: base64.b64encode(dato).decode("ascii")}))

    def test_limite_se_mide_en_bytes_utf8_y_el_sobre_entra_en_16kb(self):
        for texto in ("a" * MAX_TEXTO_BYTES, "ñ" * (MAX_TEXTO_BYTES // 2),
                       "😀" * (MAX_TEXTO_BYTES // 4)):
            mensaje = cifrar_mensaje(texto, 2)
            self.assertLessEqual(len(mensaje.a_texto()), MAX_SOBRE_BYTES)
            self.assertEqual(descifrar_mensaje(MensajeCifrado.desde_texto(mensaje.a_texto()), 2), texto)
        for texto in ("a" * (MAX_TEXTO_BYTES + 1), "ñ" * (MAX_TEXTO_BYTES // 2 + 1),
                       "\ud800", None, b"texto"):
            with self.subTest(tipo=type(texto)), self.assertRaises(ErrorMensajeCifrado):
                cifrar_mensaje(texto, 2)

    def test_rechaza_contexto_invalido_y_objetos_sin_validar(self):
        mensaje = cifrar_mensaje("Hola", 2)
        for contexto in (None, "sesion", b"x" * 4097):
            with self.subTest(tipo=type(contexto)):
                with self.assertRaises(ErrorMensajeCifrado):
                    cifrar_mensaje("Hola", 2, contexto=contexto)
                with self.assertRaises(ErrorMensajeCifrado):
                    descifrar_mensaje(mensaje, 2, contexto=contexto)
        with self.assertRaises(ErrorMensajeCifrado):
            descifrar_mensaje(mensaje.a_texto(), 2)

    def test_alice_bob_y_eve_usan_las_mismas_funciones_con_sus_secretos(self):
        alice, bob = Participante("Alice"), Participante("Bob")
        for actor, privada in ((alice, 6), (bob, 15)):
            actor.establecer_parametros(23, 5)
            actor.establecer_privada(privada)
            actor.calcular_publica()
        alice.recibir_publica(bob.publica)
        bob.recibir_publica(alice.publica)
        alice.derivar_secreto()
        bob.derivar_secreto()
        contexto = b"sesion-demo:Alice->Bob"
        envio = cifrar_mensaje("Hola, Bob. Mensaje de Alice.", alice.secreto, contexto=contexto)
        capturado = MensajeCifrado.desde_texto(envio.a_texto())
        self.assertEqual(descifrar_mensaje(capturado, bob.secreto, contexto=contexto),
                         "Hola, Bob. Mensaje de Alice.")
        with self.assertRaises(ErrorAutenticacion):
            descifrar_mensaje(capturado, 3, contexto=contexto)
        # Eve solo dispone de p, g, A y B; obtiene a mediante el ataque existente.
        exponente, _ = log_discreto_fuerza_bruta(alice.g, alice.publica, alice.p, 100)
        secreto_eve = potencia_modular(bob.publica, exponente, alice.p)
        self.assertEqual(descifrar_mensaje(capturado, secreto_eve, contexto=contexto),
                         "Hola, Bob. Mensaje de Alice.")
        respuesta = cifrar_mensaje("Hola, Alice", bob.secreto, contexto=b"sesion-demo:Bob->Alice")
        self.assertEqual(descifrar_mensaje(respuesta, alice.secreto, contexto=b"sesion-demo:Bob->Alice"),
                         "Hola, Alice")


if __name__ == "__main__":
    unittest.main()
