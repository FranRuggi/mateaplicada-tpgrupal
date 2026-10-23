"""
Motor matemático: aritmética modular para Diffie-Hellman.

ESTADO ACTUAL: MOCK
-------------------
Las funciones de este archivo usan herramientas de Python (pow con 3
argumentos, random) que la consigna NO permite en la entrega final:
"la matemática modular debe ser hecha desde cero, sin utilizar bibliotecas".

Están acá solo para que la interfaz gráfica funcione mientras el grupo
implementa el módulo real. Para reemplazarlo:
  1. Reescribir el cuerpo de cada función respetando su FIRMA
     (mismos parámetros, mismo tipo de retorno).
  2. Poner MOCK = False.
La GUI y el protocolo no se enteran del cambio.
"""
from dataclasses import dataclass
import random  # TODO(motor): ¿se permite random/secrets? -> ver PREGUNTAS.md

MOCK = True


@dataclass
class Paso:
    """Un paso de un cálculo, para mostrar en el panel 'Paso a paso'."""
    descripcion: str
    valor: int | None = None


# ---------------------------------------------------------------------------
# Exponenciación modular
# ---------------------------------------------------------------------------
def mod_pow(base: int, exp: int, mod: int) -> tuple[int, list[Paso]]:
    """Devuelve (base^exp mod mod, lista de pasos).

    TODO(motor): implementar square-and-multiply propio. Cada iteración
    del algoritmo debería agregar un Paso para que la GUI lo muestre.
    """
    bits = bin(exp)[2:]
    pasos = [Paso(f"Exponente en binario ({len(bits)} bits): {_corto(bits, 40)}")]
    max_pasos = 12
    for i, bit in enumerate(reversed(bits)):
        if i >= max_pasos:
            pasos.append(Paso(f"… {len(bits) - max_pasos} bits más (se omiten)"))
            break
        cuadrado = pow(base, 2 ** i, mod)  # MOCK
        accion = "se multiplica al acumulador" if bit == "1" else "se saltea"
        pasos.append(Paso(f"bit {i} = {bit} → base^(2^{i}) mod p, {accion}", cuadrado))
    resultado = pow(base, exp, mod)  # MOCK
    pasos.append(Paso("Resultado", resultado))
    return resultado, pasos


# ---------------------------------------------------------------------------
# Primos y generadores
# ---------------------------------------------------------------------------
def es_primo(n: int, rondas: int = 20) -> bool:
    """Test de primalidad (Miller-Rabin).

    TODO(motor): implementar usando nuestro mod_pow.
    """
    if n < 2:
        return False
    for chico in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % chico == 0:
            return n == chico
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(rondas):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)  # MOCK
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)  # MOCK
            if x == n - 1:
                break
        else:
            return False
    return True


def generar_parametros(bits: int) -> tuple[int, int, list[Paso]]:
    """Genera un primo seguro p = 2q + 1 de `bits` bits y un generador g.

    Devuelve (p, g, pasos).
    TODO(motor): reemplazar por la implementación propia.
    """
    pasos: list[Paso] = []
    intentos = 0
    while True:
        intentos += 1
        q = random.getrandbits(bits - 1) | (1 << (bits - 2)) | 1
        if es_primo(q) and es_primo(2 * q + 1):
            p = 2 * q + 1
            break
    pasos.append(Paso(f"Se probaron {intentos} candidatos hasta encontrar q primo con 2q+1 primo"))
    pasos.append(Paso("q (primo de Sophie Germain)", q))
    pasos.append(Paso("p = 2q + 1 (primo seguro)", p))
    g = encontrar_generador(p)
    pasos.append(Paso("g: primer candidato con g² ≠ 1 y g^q ≠ 1 (mod p)", g))
    return p, g, pasos


def encontrar_generador(p: int) -> int:
    """Para p = 2q+1, g genera el grupo si g^2 != 1 y g^q != 1 (mod p).

    TODO(motor): usar nuestro mod_pow.
    """
    q = (p - 1) // 2
    for g in range(2, p - 1):
        if pow(g, 2, p) != 1 and pow(g, q, p) != 1:  # MOCK
            return g
    raise ValueError("No se encontró generador (¿p es primo seguro?)")


def generar_privada(p: int) -> int:
    """Clave privada aleatoria en [2, p-2].

    TODO(motor): definir fuente de aleatoriedad permitida.
    """
    return random.randrange(2, p - 1)


# ---------------------------------------------------------------------------
# Ataque (para la vista de Eve)
# ---------------------------------------------------------------------------
def log_discreto_fuerza_bruta(g: int, objetivo: int, p: int, max_intentos: int,
                              cancelado=lambda: False) -> tuple[int | None, int]:
    """Busca x tal que g^x ≡ objetivo (mod p) probando x = 1, 2, 3...

    Devuelve (x o None, intentos realizados). Esta función ya no usa
    bibliotecas: solo multiplicación y resto.
    """
    actual = 1
    for x in range(1, max_intentos + 1):
        actual = (actual * g) % p
        if actual == objetivo:
            return x, x
        if x % 50_000 == 0 and cancelado():
            return None, x
    return None, max_intentos


def _corto(texto: str, largo: int) -> str:
    return texto if len(texto) <= largo else texto[: largo // 2] + "…" + texto[-largo // 2:]
