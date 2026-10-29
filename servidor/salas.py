"""Estado público de salas. Se ejecuta en UN único bucle de eventos."""
from collections import deque
from dataclasses import dataclass, field
import secrets
import string
import time
from uuid import uuid4


class ErrorSala(ValueError):
    pass


@dataclass
class Conexion:
    id: str = field(default_factory=lambda: uuid4().hex)
    sala: str | None = None
    rol: str | None = None
    emitir: object = None
    solicitudes: deque = field(default_factory=deque)


@dataclass
class Sala:
    codigo: str
    miembros: dict = field(default_factory=dict)
    roles: dict = field(default_factory=dict)
    partida: str | None = None
    publicos: dict = field(default_factory=dict)
    secuencia: int = 0


class Salas:
    """Las mutaciones no contienen await: elegir un rol es una operación atómica.

    emitir() encola mensajes sin esperar a la red; cada socket tiene un emisor
    independiente. No se reciben privadas ni secretos en este protocolo.
    """
    def __init__(self, max_salas=100):
        self.salas = {}
        self.max_salas = max_salas

    def estado(self, c):
        sala = self.salas.get(c.sala)
        return {"evento": "estado", "sala": c.sala, "rol": c.rol,
                "roles": {r: bool(sala and r in sala.roles) for r in ("Alice", "Bob")},
                "partida": sala.partida if sala else None}

    def _avisar(self, sala):
        for c in tuple(sala.miembros.values()):
            c.emitir(self.estado(c))

    def desconectar(self, c):
        sala = self.salas.get(c.sala)
        if sala:
            sala.miembros.pop(c.id, None)
            if c.rol and sala.roles.get(c.rol) == c.id:
                del sala.roles[c.rol]
            sala.partida = None
            sala.publicos.clear()
            sala.secuencia = 0
            if sala.miembros:
                self._avisar(sala)
            else:
                del self.salas[sala.codigo]
        c.sala = c.rol = None

    def ejecutar(self, c, pedido):
        ahora = time.monotonic()
        while c.solicitudes and ahora-c.solicitudes[0] > 10:
            c.solicitudes.popleft()
        if len(c.solicitudes) >= 60:
            raise ErrorSala("Demasiadas solicitudes. Esperá unos segundos.")
        c.solicitudes.append(ahora)
        if not isinstance(pedido, dict):
            raise ErrorSala("La solicitud debe ser un objeto JSON.")
        accion = pedido.get("accion")
        campos = {"crear": {"accion"}, "unir": {"accion", "sala"},
                  "elegir": {"accion", "rol"}, "estado": {"accion"},
                  "ping": {"accion"}, "publicar": {"accion", "partida", "tipo", "datos"}}
        if accion not in campos or set(pedido) != campos[accion]:
            raise ErrorSala("Solicitud desconocida o campos no permitidos.")
        if accion == "ping":
            c.emitir({"evento": "pong"})
        elif accion == "estado":
            c.emitir(self.estado(c))
        elif accion in ("crear", "unir"):
            if c.sala:
                raise ErrorSala("Ya estás dentro de una sala.")
            if accion == "crear":
                if len(self.salas) >= self.max_salas:
                    raise ErrorSala("El servidor está completo. Probá más tarde.")
                alfabeto = string.ascii_uppercase.replace("I", "").replace("O", "")+"23456789"
                codigo = "".join(secrets.choice(alfabeto) for _ in range(8))
                while codigo in self.salas:
                    codigo = "".join(secrets.choice(alfabeto) for _ in range(8))
                sala = self.salas[codigo] = Sala(codigo)
            else:
                codigo = pedido["sala"]
                if not isinstance(codigo, str) or len(codigo) != 8:
                    raise ErrorSala("Ingresá un código de sala de 8 caracteres.")
                sala = self.salas.get(codigo.upper())
                if sala is None:
                    raise ErrorSala("La sala no existe o ya se cerró.")
            if len(sala.miembros) >= 2:
                raise ErrorSala("La sala ya tiene dos participantes.")
            c.sala = sala.codigo
            sala.miembros[c.id] = c
            self._avisar(sala)
        elif accion == "elegir":
            sala = self._sala(c)
            rol = pedido["rol"]
            if rol not in ("Alice", "Bob"):
                raise ErrorSala("Elegí Alice o Bob.")
            if c.rol:
                raise ErrorSala("Ya elegiste personaje. Salí de la sala para cambiarlo.")
            if rol in sala.roles:
                raise ErrorSala(f"{rol} ya fue elegido. Elegí el otro personaje.")
            c.rol = rol
            sala.roles[rol] = c.id
            if len(sala.roles) == 2:
                sala.partida = uuid4().hex
            self._avisar(sala)
        elif accion == "publicar":
            self._publicar(c, pedido)

    def _sala(self, c):
        if not c.sala or c.sala not in self.salas:
            raise ErrorSala("Primero creá una sala o ingresá a una.")
        return self.salas[c.sala]

    @staticmethod
    def _numero(valor):
        # Limitar antes de convertir o hacer cuentas con datos de Internet.
        if type(valor) is int:
            if valor.bit_length() > 4096:
                raise ErrorSala("Los números admiten hasta 4096 bits.")
            return valor
        if isinstance(valor, str) and valor.isascii() and valor.isdecimal() and len(valor) <= 1234:
            n = int(valor)
            if n.bit_length() <= 4096:
                return n
        raise ErrorSala("Los datos públicos deben ser enteros de hasta 4096 bits.")

    def _publicar(self, c, pedido):
        sala = self._sala(c)
        if not c.rol or not sala.partida or pedido["partida"] != sala.partida:
            raise ErrorSala("La partida terminó o todavía falta otro participante.")
        tipo, datos = pedido["tipo"], pedido["datos"]
        esperados = {"p", "g"} if tipo == "PARAMETROS" else {"A" if c.rol == "Alice" else "B"}
        if tipo not in ("PARAMETROS", "PUBLICA") or not isinstance(datos, dict) or set(datos) != esperados:
            raise ErrorSala("Solo pueden enviarse p, g y la pública del propio personaje.")
        numeros = {k: self._numero(v) for k, v in datos.items()}
        if tipo == "PARAMETROS":
            if c.rol != "Alice":
                raise ErrorSala("Solo Alice puede publicar los parámetros.")
            p, g = numeros["p"], numeros["g"]
            if p < 5 or p % 2 == 0 or not 1 < g < p-1:
                raise ErrorSala("Los parámetros públicos están fuera de rango.")
            if "p" in sala.publicos and any(sala.publicos[k] != numeros[k] for k in ("p", "g")):
                raise ErrorSala("Para cambiar los parámetros, creá una sala nueva.")
        else:
            p = sala.publicos.get("p")
            if p is None or not 1 < next(iter(numeros.values())) < p-1:
                raise ErrorSala("Primero deben publicarse los parámetros; la pública debe estar entre 2 y p-2.")
        sala.publicos.update(numeros)
        sala.secuencia += 1
        evento = {"evento": "mensaje", "partida": sala.partida, "secuencia": sala.secuencia,
                  "remitente": c.rol, "destinatario": "Bob" if c.rol == "Alice" else "Alice",
                  "tipo": tipo, "datos": {k: str(v) for k, v in numeros.items()}}
        for miembro in tuple(sala.miembros.values()):
            miembro.emitir(evento)
