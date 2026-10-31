"""Cifrado autenticado de bytes: AES-256-GCM, sin GUI ni transporte."""

from core.clave_simetrica import TAM_CLAVE

TAM_NONCE = 12
TAM_ETIQUETA = 16


class ErrorCifrado(ValueError):
    """Datos o parámetros que no permiten realizar el cifrado."""


class ErrorAutenticacion(ErrorCifrado):
    """No se puede entregar texto sin verificar su autenticidad."""


def _validar(datos: bytes, clave: bytes, nonce: bytes, datos_asociados: bytes):
    if not isinstance(datos, bytes):
        raise ErrorCifrado("Los datos deben ser bytes.")
    if not isinstance(clave, bytes) or len(clave) != TAM_CLAVE:
        raise ErrorCifrado("La clave AES-256 debe contener exactamente 32 bytes.")
    if not isinstance(nonce, bytes) or len(nonce) != TAM_NONCE:
        raise ErrorCifrado("El nonce debe contener exactamente 12 bytes.")
    if not isinstance(datos_asociados, bytes):
        raise ErrorCifrado("Los datos asociados deben ser bytes.")


def cifrar_bytes(datos: bytes, clave: bytes, nonce: bytes, *, datos_asociados: bytes = b"") -> bytes:
    """Devolver texto cifrado + etiqueta de 16 bytes.

    El llamador debe asegurar que no se repita el par clave/nonce. Los datos
    asociados se autentican pero no se cifran; deben coincidir al descifrar.
    Para texto y generación automática de sal/nonce, usar cifrar_mensaje().
    """
    _validar(datos, clave, nonce, datos_asociados)
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(clave).encrypt(nonce, datos, datos_asociados)


def descifrar_bytes(datos: bytes, clave: bytes, nonce: bytes, *, datos_asociados: bytes = b"") -> bytes:
    """Devolver bytes originales solo si la autenticación resulta válida.

    Clave, nonce, contenido o datos asociados incorrectos producen el mismo
    ErrorAutenticacion. Nunca se devuelve un texto parcialmente descifrado.
    """
    _validar(datos, clave, nonce, datos_asociados)
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        return AESGCM(clave).decrypt(nonce, datos, datos_asociados)
    except InvalidTag as error:
        raise ErrorAutenticacion(
            "No se pudo autenticar el mensaje: la clave, el contexto o el contenido no coinciden."
        ) from error
