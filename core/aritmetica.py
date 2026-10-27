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

MOCK = False


@dataclass
class Paso:
    """Un paso de un cálculo, para mostrar en el panel 'Paso a paso'."""
    descripcion: str
    valor: int | None = None


# ---------------------------------------------------------------------------
# Exponenciación modular
# ---------------------------------------------------------------------------
def mod_pow(base: int, exp: int, mod: int) -> tuple[int, list[Paso]]:
    """Devuelve (base^exp mod mod, lista de pasos trabajando directamente con el número)."""
    if mod == 1:
        return 0, [Paso("Módulo es 1, el resultado es 0")]

    pasos = [Paso(f"Exponente inicial: e = {exp} (binario: {bin(exp)[2:]})")]
    max_pasos = 12
    r = 1
    g = base % mod
    e = exp
    i = 0
    while e > 0:
        if i >= max_pasos:
            pasos.append(Paso(f"… Se superó el límite de {max_pasos} pasos (se omiten los restantes)"))
            break
        r_anterior = r
        if e & 1: #si es impar mostrar como se actualiza o no r
            r = (r * g) % mod
            accion_r = f"e es IMPAR (bit = 1) -> r se actualiza: ({r_anterior} * {g}) mod {mod} = {r}"
        else:
            accion_r = f"e es PAR (bit = 0) -> r se MANTIENE en {r}"
        #actualizar e
        e_anterior = e
        e = e >> 1  #dividir x 2 y tira el ultimo si es impar (bit shift)
        g_anterior = g
        g = (g * g) % mod
        #mostrar que hicimos
        detalle = (
            f"Iteración {i} (e={e_anterior}): "
            f"{accion_r} | e pasa a {e} | g pasa a {g}"
        )
        pasos.append(Paso(detalle, r))
        i += 1

    #Llamamos a la función para asegurar el resultado final
    #(por si se cortó la lista por el max_pasos)
    resultado = potencia_modular(base, exp, mod)
    pasos.append(Paso("Resultado", resultado))
    return resultado, pasos

def potencia_modular(base: int, exp: int, mod: int) -> int:
    if mod == 1:
        return 0
    resultado = 1 #r segun notacion de la catedra
    base = base % mod #hacer g^2
    while exp > 0: #e
        #si e es impar -> hacer (e-1)/2 y actualizar r
        if exp & 1: #si el ultimo bit es 1, osea, es impar
            resultado = (resultado * base) % mod
        exp = exp >> 1 #no importa si es par o impar aca pq si es impar se cae el ultimo bit y es como hacer (expo-1)/2
        #hacer g^2 en modulo dado siempre
        base = (base * base) % mod
    return resultado
# ---------------------------------------------------------------------------
# Primos y generadores
# ---------------------------------------------------------------------------
def es_primo(n: int, rondas: int = 20) -> bool:
    """Test de primalidad (Miller-Rabin)."""
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
        x = potencia_modular(a, d, n)  # con funcion propia ahora
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = potencia_modular(x, 2, n)  # con funcion propia ahora
            if x == n - 1:
                break
        else:
            return False
    return True


def generar_parametros(bits: int) -> tuple[int, int, list[Paso]]:
    """Genera un primo seguro p = 2q + 1 de `bits` bits y un generador g."""
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
    """Para p = 2q+1, g genera el grupo si g^2 != 1 y g^q != 1 (mod p)."""
    q = (p - 1) // 2
    for g in range(2, p - 1):
        if potencia_modular(g, 2, p) != 1 and potencia_modular(g, q, p) != 1:  #con funcion propia ahora
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
