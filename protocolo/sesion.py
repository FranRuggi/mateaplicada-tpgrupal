"""
Protocolo Diffie-Hellman: estado de cada participante.

No hace cuentas por su cuenta: todo lo matemático lo delega en
core.aritmetica, así cuando se reemplace el mock no hay que tocar nada acá.
"""
from enum import Enum

from core import aritmetica
from core.aritmetica import Paso


class ErrorProtocolo(Exception):
    """Error pensado para mostrarse tal cual al usuario en la GUI."""


class Estado(Enum):
    SIN_PARAMETROS = "Esperando parámetros"
    CON_PARAMETROS = "Parámetros acordados"
    PUBLICA_LISTA = "Clave pública calculada"
    SECRETO_LISTO = "Secreto derivado"


class Participante:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.reiniciar()

    def reiniciar(self):
        self.p: int | None = None
        self.g: int | None = None
        self.privada: int | None = None
        self.publica: int | None = None
        self.publica_ajena: int | None = None
        self.secreto: int | None = None

    # -- estado --------------------------------------------------------------
    @property
    def estado(self) -> Estado:
        if self.secreto is not None:
            return Estado.SECRETO_LISTO
        if self.publica is not None:
            return Estado.PUBLICA_LISTA
        if self.p is not None:
            return Estado.CON_PARAMETROS
        return Estado.SIN_PARAMETROS

    # -- pasos del protocolo ---------------------------------------------------
    def establecer_parametros(self, p: int, g: int):
        if p < 5:
            raise ErrorProtocolo("p tiene que ser un primo mayor que 3.")
        if not aritmetica.es_primo(p):
            raise ErrorProtocolo("p no es primo.")
        if not 1 < g < p - 1:
            raise ErrorProtocolo("g tiene que cumplir 1 < g < p-1.")
        self.reiniciar()
        self.p, self.g = p, g

    def establecer_privada(self, valor: int):
        self._requiere_parametros()
        if not 1 < valor < self.p - 1:
            raise ErrorProtocolo(f"La clave privada tiene que estar entre 2 y p-2.")
        self.privada = valor
        # Cambiar la privada invalida lo calculado, pero NO lo recibido del otro.
        self.publica = self.secreto = None

    def generar_privada(self) -> int:
        self._requiere_parametros()
        self.establecer_privada(aritmetica.generar_privada(self.p))
        return self.privada

    def calcular_publica(self) -> tuple[int, list[Paso]]:
        self._requiere_parametros()
        if self.privada is None:
            raise ErrorProtocolo(f"{self.nombre} todavía no eligió su clave privada.")
        self.publica, pasos = aritmetica.mod_pow(self.g, self.privada, self.p)
        return self.publica, pasos

    def recibir_publica(self, valor: int):
        self._requiere_parametros()
        # Validación: valores 0, 1 o p-1 harían trivial el secreto.
        if not 1 < valor < self.p - 1:
            raise ErrorProtocolo("La clave pública recibida es inválida (fuera de 2..p-2).")
        self.publica_ajena = valor

    def derivar_secreto(self) -> tuple[int, list[Paso]]:
        if self.publica_ajena is None:
            raise ErrorProtocolo(f"{self.nombre} todavía no recibió la clave pública del otro.")
        if self.privada is None:
            raise ErrorProtocolo(f"{self.nombre} todavía no eligió su clave privada.")
        self.secreto, pasos = aritmetica.mod_pow(self.publica_ajena, self.privada, self.p)
        return self.secreto, pasos

    def _requiere_parametros(self):
        if self.p is None:
            raise ErrorProtocolo("Primero hay que acordar los parámetros públicos p y g.")
