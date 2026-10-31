"""Mensajes UTF-8 cifrados, con un sobre público JSON independiente del canal.

Versión 1: HKDF-SHA256, sal de 32 bytes y AES-256-GCM con nonce de 12 bytes.
El sobre contiene solo versión, algoritmo, sal, nonce y texto cifrado con tag.
No contiene K, la clave AES, las privadas de DH ni el texto original.
La capa Conversacion lo integra con el tipo CIFRADO de los transportes.
"""
import base64
import binascii
from dataclasses import dataclass
import json
import secrets

from core.clave_simetrica import derivar_clave
from core.cifrado import ErrorCifrado, TAM_ETIQUETA, TAM_NONCE, cifrar_bytes, descifrar_bytes

VERSION = 1
ALGORITMO = "AES-256-GCM"
TAM_SAL = 32
MAX_TEXTO_BYTES = 8192
MAX_SOBRE_BYTES = 16_384
MAX_CONTEXTO_BYTES = 4096
_CABECERA = b"TP-Diffie-Hellman/mensaje/v1/AES-256-GCM\x00"
_CAMPOS = {"version", "algoritmo", "sal", "nonce", "texto_cifrado"}


class ErrorMensajeCifrado(ErrorCifrado):
    """Texto o sobre que no cumple el formato de mensajes cifrados."""


def _sin_repetidas(pares):
    resultado = {}
    for clave, valor in pares:
        if clave in resultado:
            raise ErrorMensajeCifrado("El sobre contiene campos repetidos.")
        resultado[clave] = valor
    return resultado


def _decodificar_base64(valor):
    if not isinstance(valor, str):
        raise ErrorMensajeCifrado("Los campos binarios del sobre deben ser texto Base64.")
    try:
        datos = base64.b64decode(valor, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ErrorMensajeCifrado("El sobre contiene un campo Base64 inválido.") from error
    if base64.b64encode(datos).decode("ascii") != valor:
        raise ErrorMensajeCifrado("El campo Base64 no tiene una representación canónica.")
    return datos


def _datos_asociados(contexto: bytes) -> bytes:
    if not isinstance(contexto, bytes) or len(contexto) > MAX_CONTEXTO_BYTES:
        raise ErrorMensajeCifrado("El contexto debe ser bytes, hasta 4096 bytes.")
    return _CABECERA + contexto


@dataclass(frozen=True)
class MensajeCifrado:
    """Sobre inmutable: todos sus campos pueden ser observados por Eve."""
    sal: bytes
    nonce: bytes
    texto_cifrado: bytes

    def __post_init__(self):
        if not isinstance(self.sal, bytes) or len(self.sal) != TAM_SAL:
            raise ErrorMensajeCifrado("La sal del mensaje debe contener exactamente 32 bytes.")
        if not isinstance(self.nonce, bytes) or len(self.nonce) != TAM_NONCE:
            raise ErrorMensajeCifrado("El nonce del mensaje debe contener exactamente 12 bytes.")
        if (not isinstance(self.texto_cifrado, bytes) or
                not TAM_ETIQUETA <= len(self.texto_cifrado) <= MAX_TEXTO_BYTES + TAM_ETIQUETA):
            raise ErrorMensajeCifrado("El contenido cifrado está incompleto o supera el tamaño admitido.")

    def a_texto(self) -> str:
        """Serializar en una línea ASCII, sin claves ni texto original."""
        return json.dumps({
            "version": VERSION, "algoritmo": ALGORITMO,
            "sal": base64.b64encode(self.sal).decode("ascii"),
            "nonce": base64.b64encode(self.nonce).decode("ascii"),
            "texto_cifrado": base64.b64encode(self.texto_cifrado).decode("ascii"),
        }, sort_keys=True, separators=(",", ":"))

    @classmethod
    def desde_texto(cls, texto: str) -> "MensajeCifrado":
        """Validar estructura y tamaños antes de aceptar un sobre del canal."""
        if not isinstance(texto, str) or len(texto) > MAX_SOBRE_BYTES or not texto.isascii():
            raise ErrorMensajeCifrado("El sobre debe ser texto JSON ASCII de hasta 16 KB.")
        try:
            datos = json.loads(texto, object_pairs_hook=_sin_repetidas)
        except (ValueError, RecursionError) as error:
            raise ErrorMensajeCifrado("El sobre no es JSON válido o contiene campos repetidos.") from error
        if not isinstance(datos, dict) or set(datos) != _CAMPOS:
            raise ErrorMensajeCifrado("El sobre no contiene los campos esperados.")
        if type(datos["version"]) is not int or datos["version"] != VERSION:
            raise ErrorMensajeCifrado("La versión del mensaje cifrado no es compatible.")
        if datos["algoritmo"] != ALGORITMO:
            raise ErrorMensajeCifrado("El algoritmo del mensaje cifrado no es compatible.")
        return cls(*(_decodificar_base64(datos[campo]) for campo in ("sal", "nonce", "texto_cifrado")))


def cifrar_mensaje(texto: str, secreto: int, *, contexto: bytes = b"") -> MensajeCifrado:
    """Cifrar texto con K; generar una sal y un nonce nuevos para cada envío.

    contexto puede identificar la sesión y el remitente. Ambos participantes
    deben acordarlo y proporcionarlo idéntico al descifrar; no es secreto.
    Se admiten hasta 8192 bytes UTF-8, incluido el texto vacío.
    """
    if not isinstance(texto, str):
        raise ErrorMensajeCifrado("El mensaje debe ser texto.")
    # Todo carácter UTF-8 ocupa al menos un byte: limitar antes de codificar.
    if len(texto) > MAX_TEXTO_BYTES:
        raise ErrorMensajeCifrado("El mensaje admite hasta 8192 bytes UTF-8.")
    try:
        datos = texto.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ErrorMensajeCifrado("El mensaje no se puede representar en UTF-8.") from error
    if len(datos) > MAX_TEXTO_BYTES:
        raise ErrorMensajeCifrado("El mensaje admite hasta 8192 bytes UTF-8.")
    asociados = _datos_asociados(contexto)
    sal, nonce = secrets.token_bytes(TAM_SAL), secrets.token_bytes(TAM_NONCE)
    clave = derivar_clave(secreto, sal)
    return MensajeCifrado(sal, nonce, cifrar_bytes(datos, clave, nonce, datos_asociados=asociados))


def descifrar_mensaje(mensaje: MensajeCifrado, secreto: int, *, contexto: bytes = b"") -> str:
    """Autenticar y recuperar el texto usando K y el mismo contexto del envío."""
    if not isinstance(mensaje, MensajeCifrado):
        raise ErrorMensajeCifrado("Se esperaba un MensajeCifrado validado.")
    asociados = _datos_asociados(contexto)
    clave = derivar_clave(secreto, mensaje.sal)
    datos = descifrar_bytes(mensaje.texto_cifrado, clave, mensaje.nonce, datos_asociados=asociados)
    try:
        return datos.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ErrorMensajeCifrado("El mensaje autenticado no contiene texto UTF-8 válido.") from error
