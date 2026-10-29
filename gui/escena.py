"""Escena arcade de DH. Presenta eventos del protocolo sin hacer aritmética."""
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import math
import time
import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk

from gui import tema
from transporte.canal import Mensaje


@dataclass(frozen=True)
class EventoEscena:
    tipo: str
    actor: str
    datos: tuple[tuple[str, int], ...] = ()


class EscenaIntercambio(ctk.CTkFrame):
    """Sprites y paquetes en una cola visual; Tk sigue atendiendo la ventana.

    El estado de los actores viene de Participante. Eve solo recibe copias de
    mensajes públicos, nunca referencias al estado privado de Alice o Bob.
    """

    def __init__(self, master, al_cambiar=None):
        super().__init__(master, fg_color="#172640", corner_radius=10, height=330)
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg="#172640", highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.canvas.bind("<Configure>", lambda _e: self._dibujar())
        ruta = Path(__file__).resolve().parents[1] / "assets" / "personajes-arcade.png"
        self._hoja = tk.PhotoImage(master=self.canvas, file=str(ruta))
        self._sprites = {}
        self._fuentes = {}
        self.al_cambiar = al_cambiar
        self.animaciones = True
        self._cola = deque()
        self._evento = None
        self._after_id = None
        self._latido_id = None
        self._ataque = {"estado": "esperando", "intentos": 0}
        self._t = 0.0
        self._inicio = 0.0
        self._estado = {}
        self.publicos_observados = {}
        self.reiniciar()

    @property
    def en_animacion(self):
        return self._evento is not None or bool(self._cola)

    def actualizar(self, alice, bob, ocultar_privadas=(True, True)):
        anterior = self._estado
        self._estado = {
            p.nombre: {"p": p.p, "g": p.g, "privada": p.privada,
                       "publica": p.publica, "secreto": p.secreto, "oculta": oculta}
            for p, oculta in zip((alice, bob), ocultar_privadas)
        }
        for nombre, datos in self._estado.items():
            previo = anterior.get(nombre, {})
            for campo in ("publica", "secreto"):
                if datos[campo] is not None and datos[campo] != previo.get(campo):
                    self._agregar(EventoEscena(campo, nombre))
        self._dibujar()

    def mostrar_mensaje(self, mensaje: Mensaje):
        mensaje.validar()
        # Copia inmutable: ni una posterior mutación del mensaje ni un cambio de
        # privada pueden alterar lo que ya se vio viajar por el canal.
        self._agregar(EventoEscena("mensaje", mensaje.remitente, tuple(mensaje.datos.items())))

    def establecer_animaciones(self, habilitar):
        self.animaciones = bool(habilitar)
        if not self.animaciones:
            self._cancelar_reloj()
            if self._evento is not None:
                self._aplicar(self._evento)
                self._evento = None
            while self._cola:
                self._aplicar(self._cola.popleft())
            self._dibujar()
            self._avisar()
        self._actualizar_latido()

    def actualizar_ataque(self, estado):
        anterior = self._ataque
        self._ataque = dict(estado)
        nuevo = estado.get("estado")
        if nuevo == "encontrada" and (anterior.get("estado") != nuevo or
                                      anterior.get("exponente") != estado.get("exponente")):
            self._agregar(EventoEscena("ataque_exito", "Eve"))
        elif nuevo == "limite" and anterior.get("estado") != nuevo:
            self._agregar(EventoEscena("ataque_limite", "Eve"))
        self._actualizar_latido()
        self._dibujar()

    def _actualizar_latido(self):
        buscando = self.animaciones and self._ataque.get("estado") == "buscando"
        if buscando and self._latido_id is None:
            self._latido_id = self.after(40, self._latir)
        elif not buscando and self._latido_id is not None:
            self.after_cancel(self._latido_id)
            self._latido_id = None

    def _latir(self):
        self._latido_id = None
        self._dibujar()
        self._actualizar_latido()

    def reiniciar(self):
        self._cancelar_reloj()
        self._ataque = {"estado": "esperando", "intentos": 0}
        self._actualizar_latido()
        self._cola.clear()
        self._evento = None
        self._estado = {}
        self.publicos_observados.clear()
        self._t = 0
        self._dibujar()

    def _agregar(self, evento):
        if not self.animaciones:
            self._aplicar(evento)
            self._dibujar()
            return
        self._cola.append(evento)
        if self._evento is None:
            self._comenzar()
        self._avisar()

    def _comenzar(self):
        if not self._cola:
            return
        self._evento = self._cola.popleft()
        self._inicio = time.monotonic()
        self._t = 0
        self._dibujar()
        self._after_id = self.after(16, self._avanzar)

    def _avanzar(self):
        self._after_id = None
        if self._evento is None:
            return
        duracion = 1.75 if self._evento.tipo == "mensaje" else 0.48
        self._t = min(1.0, (time.monotonic() - self._inicio) / duracion)
        if self._t >= 1:
            self._aplicar(self._evento)
            self._evento = None
            self._comenzar()
            self._avisar()
        else:
            self._after_id = self.after(16, self._avanzar)
        self._dibujar()

    def _aplicar(self, evento):
        if evento.tipo == "mensaje":
            self.publicos_observados.update(evento.datos)

    def _avisar(self):
        if self.al_cambiar:
            self.al_cambiar()

    def _cancelar_reloj(self):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def destroy(self):
        self._cancelar_reloj()
        self._ataque = {}
        self._actualizar_latido()
        super().destroy()

    # -- dibujo ----------------------------------------------------------------
    def _fuente(self, tam=12, negrita=False):
        escala = self._get_widget_scaling()
        clave = (tam, negrita, escala)
        if clave not in self._fuentes:
            self._fuentes[clave] = tkfont.Font(root=self.canvas, family=tema.MONO,
                                               size=-round(tam * escala),
                                               weight="bold" if negrita else "normal")
        return self._fuentes[clave]

    @staticmethod
    def _numero(valor, limite=16):
        if valor is None:
            return "—"
        texto = str(valor)
        if len(texto) <= limite:
            return texto
        mitad = (limite - 1) // 2
        return f"{texto[:mitad]}…{texto[-mitad:]}"

    def _encajar(self, texto, ancho, fuente):
        if fuente.measure(texto) <= ancho:
            return texto
        limite = len(texto)
        while limite > 3:
            limite -= 1
            mitad = (limite - 1) // 2
            corto = texto[:mitad] + "…" + texto[-mitad:]
            if fuente.measure(corto) <= ancho:
                return corto
        return "…"

    def _sprite(self, nombre, alto):
        celda = self._hoja.width() // 3
        factor = max(1, round(celda / alto))
        clave = (nombre, factor)
        if clave not in self._sprites:
            indice = {"Alice": 0, "Eve": 1, "Bob": 2}[nombre]
            imagen = tk.PhotoImage(master=self.canvas)
            imagen.tk.call(imagen, "copy", self._hoja, "-from", indice * celda, 0,
                            (indice + 1) * celda, self._hoja.height(),
                            "-subsample", factor, factor)
            self._sprites[clave] = imagen
        return self._sprites[clave]

    def _salto(self, nombre):
        e, t = self._evento, self._t
        if e is None:
            return 0
        if e.tipo == "ataque_limite":
            return 0
        if e.tipo != "mensaje":
            return math.sin(math.pi * t) * 12 if nombre == e.actor else 0
        if nombre == e.actor and t < .2:
            return math.sin(math.pi * t / .2) * 10
        otro = "Bob" if e.actor == "Alice" else "Alice"
        if nombre == otro and t > .8:
            return math.sin(math.pi * (t - .8) / .2) * 10
        if nombre == "Eve" and .42 < t < .85:
            return math.sin(math.pi * (t - .42) / .43) * 13
        return 0

    def _texto(self, x, y, texto, color=tema.TEXTO, tam=12, negrita=False, **kw):
        return self.canvas.create_text(x, y, text=texto, fill=color,
                                       font=self._fuente(tam, negrita), **kw)

    def _plataforma(self, x, y, ancho, color, s):
        c = self.canvas
        c.create_rectangle(x - ancho / 2, y, x + ancho / 2, y + 11*s,
                           fill="#334968", outline="")
        c.create_rectangle(x - ancho / 2, y, x + ancho / 2, y + 3*s,
                           fill=color, outline="")
        c.create_rectangle(x - ancho / 2 + 4*s, y + 11*s,
                           x + ancho / 2 - 4*s, y + 14*s, fill="#101c31", outline="")

    def _dibujar(self):
        if not self.canvas.winfo_exists():
            return
        c = self.canvas
        s = self._get_widget_scaling()
        w, h = max(300, c.winfo_width()), max(280*s, c.winfo_height())
        c.delete("all")
        # Fondo y suelo de píxeles, sin temporizadores de adorno en reposo.
        for i in range(18):
            tono = (19 + i//2, 32 + i//2, 57 + i//2)
            c.create_rectangle(0, h*i/18, w, h*(i+1)/18,
                               fill="#%02x%02x%02x" % tono, outline="")
        for x in range(round(24*s), round(w), round(73*s)):
            c.create_rectangle(x, 63*s, x+1, 63*s+1, fill="#637899", outline="")
        c.create_rectangle(0, h-5*s, w, h, fill="#526c91", outline="")
        for x in range(0, round(w), round(32*s)):
            c.create_rectangle(x, h-3*s, x+30*s, h, fill="#2f4465", outline="")

        self._texto(w/2, 14*s, "CANAL INSEGURO", "#bdcde6", 11)
        parametros = self._estado.get("Alice", {})
        pg = f"p = {self._numero(parametros.get('p'))}   ·   g = {self._numero(parametros.get('g'))}"
        self._texto(w/2, 37*s, self._encajar(pg, w*.65, self._fuente(12)))
        canal_y = 72*s
        c.create_line(w*.17, canal_y, w*.83, canal_y, fill="#8399ba", width=1,
                      dash=(6, 6))

        for nombre, x, color, simbolo, privada in [
            ("Alice", w*.17, "#79b0ff", "A", "a"),
            ("Bob", w*.83, "#61dcb5", "B", "b"),
        ]:
            datos = self._estado.get(nombre, {})
            imagen = self._sprite(nombre, min(144*s, h*.44))
            base = h-89*s
            self._plataforma(x, base+3*s, min(150*s, w*.24), "#7697c2", s)
            self._texto(x, base-imagen.height()-14*s, nombre.upper(), color, 13, True)
            c.create_image(x, base-self._salto(nombre)*s, image=imagen, anchor="s")
            valor = "••••" if datos.get("oculta", True) and datos.get("privada") is not None else self._numero(datos.get("privada"), 12)
            self._texto(x, h-68*s, f"{privada} = {valor} · privada", "#c4d4ed", 11)
            self._texto(x, h-46*s, f"{simbolo} = {self._numero(datos.get('publica'), 18)}", color, 12,
                         tags=f"publica_{nombre}")
            secreto = datos.get("secreto")
            self._texto(x, h-22*s, f"K = {self._numero(secreto, 18) if secreto is not None else '?'}",
                         tema.OK if secreto is not None else "#9cafcd", 13, True,
                         tags=f"clave_{nombre}")

        eve = self._sprite("Eve", min(110*s, h*.34))
        base = h-53*s
        self._plataforma(w/2, base+3*s, 120*s, "#ae739a", s)
        self._texto(w/2, base-eve.height()-14*s, "EVE", "#ff8493", 13, True)
        desplazamiento = 0
        if self.animaciones and self._ataque.get("estado") == "buscando":
            desplazamiento = math.sin(time.monotonic()*8)*4*s
        elif self._evento and self._evento.tipo == "ataque_limite":
            desplazamiento = math.sin(self._t*math.pi*6)*5*s
        c.create_image(w/2+desplazamiento, base-self._salto("Eve")*s, image=eve, anchor="s")
        if self._evento and self._evento.tipo == "ataque_exito":
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                x = w/2 + dx*(35+25*self._t)*s
                y = base-55*s + dy*35*self._t*s
                c.create_rectangle(x, y, x+4*s, y+4*s, fill="#ffabbc", outline="")
        conocidos = [k for k in ("p", "g", "A", "B") if k in self.publicos_observados]
        botin = " · ".join(f"{k}={self._numero(self.publicos_observados[k], 9)}" for k in conocidos)
        self._texto(w/2, h-31*s, self._encajar(botin or "Datos capturados: —", w*.4, self._fuente(11)),
                     "#ffc2cc", 11, tags="datos_Eve")
        clave_eve = self._ataque.get("secreto") if self._ataque.get("estado") == "encontrada" else None
        self._texto(w/2, h-13*s, f"K = {self._numero(clave_eve, 18) if clave_eve is not None else '?'}",
                     "#ff8493", 12, True, tags="clave_Eve")
        if not self._evento or self._evento.tipo != "mensaje":
            frase = "A ver qué envían…" if not conocidos else "¡Ya tengo p y g!"
            if "A" in conocidos:
                frase = "¡A también es mío!"
            if "B" in conocidos:
                frase = "Tengo todo lo público…" if "A" in conocidos else "¡Ya tengo B!"
            if all(self._estado.get(n, {}).get("secreto") is not None for n in ("Alice", "Bob")):
                frase = "¡Me falta el secreto!"
            estado_ataque = self._ataque.get("estado")
            intentos = self._ataque.get("intentos", 0)
            if estado_ataque == "buscando":
                frase = (f"Último a = {intentos:,}\n"
                         f"g^a mod p = {self._numero(self._ataque.get('resto'), 12)}") if intentos else "Preparando búsqueda…"
            elif estado_ataque == "encontrada":
                frase = f"¡Encontré a = {self._ataque['exponente']}!\n{intentos:,} intentos reales"
            elif estado_ataque == "limite":
                frase = f"¡Llegué al límite!\n{intentos:,} intentos"
            elif estado_ataque == "cancelado":
                frase = "Búsqueda detenida"
            elif estado_ataque == "error":
                frase = "Falló la búsqueda"
            fuente = self._fuente(11)
            ancho = max(fuente.measure(linea) for linea in frase.splitlines()) + 18*s
            alto = (12 if '\n' not in frase else 20)*s
            y = base-eve.height()-47*s
            c.create_rectangle(w/2-ancho/2, y-alto, w/2+ancho/2, y+alto,
                               fill="#33283f", outline="#9c6c85")
            self._texto(w/2, y, frase, "#ffd0d8", 11, tags="estado_ataque_Eve")
        elif self._evento and self._evento.tipo == "mensaje":
            self._dibujar_paquetes(w, h, s, canal_y)

    def _dibujar_paquetes(self, w, h, s, y):
        e, t = self._evento, self._t
        if not .16 <= t <= .84:
            return
        progreso = min(1.0, max(0.0, (t-.16)/.68))
        inicio, fin = (w*.17, w*.83) if e.actor == "Alice" else (w*.83, w*.17)
        texto = " · ".join(f"{k}={self._numero(v, 12)}" for k, v in e.datos)
        self._paquete(inicio+(fin-inicio)*progreso, y, texto,
                       "#86b4ff" if e.actor == "Alice" else "#63dcb5", w, s)
        if t >= .5:
            copia = min(1.0, (t-.5)/.34)
            self._paquete(w/2, y+(h-108*s-y)*copia, texto, "#f29aac", w, s, copia=True)

    def _paquete(self, x, y, texto, color, w, s, copia=False):
        fuente = self._fuente(11 if copia else 13, True)
        texto = self._encajar(texto, w*.43, fuente)
        ancho, alto = fuente.measure(texto)+20*s, 28*s
        x = max(ancho/2+4, min(w-ancho/2-4, x))
        self.canvas.create_rectangle(x-ancho/2+3*s, y-alto/2+3*s,
                                      x+ancho/2+3*s, y+alto/2+3*s,
                                      fill="#0a1426", outline="", tags="paquete")
        self.canvas.create_rectangle(x-ancho/2, y-alto/2, x+ancho/2, y+alto/2,
                                      fill="#ffe0e8" if copia else "#dfedff",
                                      outline=color, width=2*s, tags="paquete")
        self._texto(x, y, texto, "#15213a", 11 if copia else 13, True, tags="paquete")
