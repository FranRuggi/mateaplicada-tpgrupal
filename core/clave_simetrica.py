"""Convertir el secreto entero de DH en una clave para cifrado simétrico.

La matemática de Diffie-Hellman sigue en aritmetica.py. Este módulo aplica
HKDF-SHA256 al entero positivo K, codificado en big endian sin ceros iniciales.
Una salida de 32 bytes no aumenta la entropía de un K pequeño de demostración.
"""

TAM_CLAVE = 32
MAX_BITS_SECRETO = 4096
CONTEXTO_DERIVACION = b"TP-Diffie-Hellman/mensajes/v1"


def derivar_clave(secreto: int, sal: bytes, *, contexto: bytes = CONTEXTO_DERIVACION) -> bytes:
    """Derivar 32 bytes desde K y una sal pública, sin modificar ni almacenar K.

    Ambas partes deben usar el mismo K, sal y contexto. La sal se genera al
    cifrar cada mensaje y viaja junto al texto cifrado. No es una contraseña.
    El contexto distingue el propósito de esta clave de otros usos de K.
    """
    if type(secreto) is not int or secreto <= 0 or secreto.bit_length() > MAX_BITS_SECRETO:
        raise ValueError("El secreto K debe ser un entero positivo de hasta 4096 bits.")
    if not isinstance(sal, bytes) or not 1 <= len(sal) <= 64:
        raise ValueError("La sal debe contener entre 1 y 64 bytes.")
    if not isinstance(contexto, bytes) or len(contexto) > 4096:
        raise ValueError("El contexto de derivación debe ser bytes, hasta 4096 bytes.")
    material = secreto.to_bytes((secreto.bit_length() + 7) // 8, "big")
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    return HKDF(algorithm=hashes.SHA256(), length=TAM_CLAVE,
                salt=sal, info=contexto).derive(material)
