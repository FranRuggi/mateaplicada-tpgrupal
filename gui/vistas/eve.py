"""Ataque de Eve: fuerza bruta del logaritmo discreto.

Muestra por qué el tamaño de p importa: con p chico Eve encuentra la clave
privada en un instante; con p grande la estimación da miles de años.
"""
import math
import time

import customtkinter as ctk

from core import aritmetica
from gui import tema
from gui.componentes import Tarjeta


class VistaEve(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure((0, 1), weight=1, uniform="c")
        self.grid_rowconfigure(0, weight=1)
        self._cancelar = False

        izq = Tarjeta(self, "Ataque por fuerza bruta",
                      "Eve conoce p, g y A. Prueba x = 1, 2, 3… hasta que g^x mod p = A.",
                      color=tema.EVE)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        f = izq.siguiente_fila
        self.entradas = {}
        for i, (k, ayuda) in enumerate([("p", "primo público"), ("g", "generador"),
                                        ("A", "clave pública interceptada")]):
            ctk.CTkLabel(izq, text=f"{k}  ·  {ayuda}", font=tema.fuente(11), text_color=tema.TENUE,
                         anchor="w").grid(row=f + 2 * i, column=0, sticky="ew", padx=16, pady=(10, 2))
            e = ctk.CTkEntry(izq, font=tema.fuente_mono(12), height=32)
            e.grid(row=f + 2 * i + 1, column=0, sticky="ew", padx=16)
            self.entradas[k] = e
        f += 6
        ctk.CTkLabel(izq, text="Máximo de intentos", font=tema.fuente(11), text_color=tema.TENUE,
                     anchor="w").grid(row=f, column=0, sticky="ew", padx=16, pady=(10, 2))
        self.sel_max = ctk.CTkSegmentedButton(izq, values=["10 mil", "1 millón", "10 millones"])
        self.sel_max.set("1 millón")
        self.sel_max.grid(row=f + 1, column=0, sticky="ew", padx=16)
        self.btn = ctk.CTkButton(izq, text="Intentar romper", height=38, fg_color=tema.EVE,
                                 text_color="#0b0f18", font=tema.fuente(14, "bold"),
                                 hover_color="#c94452", command=self._atacar)
        self.btn.grid(row=f + 2, column=0, sticky="ew", padx=16, pady=(18, 6))
        ctk.CTkLabel(izq, text="Tip: probá con p de 16 bits y después con 64.",
                     font=tema.fuente(11), text_color=tema.TENUE).grid(row=f + 3, column=0, pady=(0, 12))

        der = Tarjeta(self, "Resultado")
        der.grid(row=0, column=1, sticky="nsew")
        self.resultado = ctk.CTkTextbox(der, font=tema.fuente_mono(13), fg_color=tema.PANEL_2,
                                        corner_radius=10, wrap="word")
        self.resultado.grid(row=der.siguiente_fila, column=0, sticky="nsew", padx=12, pady=(4, 12))
        der.grid_rowconfigure(der.siguiente_fila, weight=1)
        self._escribir("Cargá p, g y A (o venite desde el modo local con\n"
                       "'Intentar el ataque de Eve') y tocá 'Intentar romper'.")

    def cargar(self, datos: dict):
        for k, e in self.entradas.items():
            if k in datos:
                e.delete(0, "end")
                e.insert(0, str(datos[k]))

    def _escribir(self, texto, agregar=False):
        self.resultado.configure(state="normal")
        if not agregar:
            self.resultado.delete("1.0", "end")
        self.resultado.insert("end", texto + "\n")
        self.resultado.configure(state="disabled")

    def _atacar(self):
        try:
            p, g, A = (int(self.entradas[k].get()) for k in ("p", "g", "A"))
        except ValueError:
            self._escribir("⚠ p, g y A tienen que ser números enteros.")
            return
        maximo = {"10 mil": 10_000, "1 millón": 1_000_000, "10 millones": 10_000_000}[self.sel_max.get()]
        self.btn.configure(state="disabled", text="Buscando…")
        self._escribir(f"p tiene {p.bit_length()} bits. Probando hasta {maximo:,} exponentes…")
        inicio = time.perf_counter()

        def listo(res):
            x, intentos = res
            seg = max(time.perf_counter() - inicio, 1e-6)
            vel = intentos / seg
            self.btn.configure(state="normal", text="Intentar romper")
            if x is not None:
                self._escribir(f"\n✔ ¡Eve encontró la clave privada!\n   a = {x}\n"
                               f"   en {intentos:,} intentos ({seg:.2f} s)\n\n"
                               "Con a puede calcular K = B^a mod p igual que Alice.", True)
            else:
                self._escribir(f"\n✘ No la encontró en {intentos:,} intentos ({seg:.2f} s).", True)
            # estimación para el tamaño de p
            esperado = p / 2
            segundos = esperado / vel
            anios = segundos / 31_557_600
            if anios < 1:
                tiempo = f"~{segundos:,.1f} segundos"
            elif anios < 1e6:
                tiempo = f"~{anios:,.0f} años"
            else:
                tiempo = f"~10^{math.log10(anios):.0f} años  (el universo tiene ~10^10)"
            self._escribir(f"\nVelocidad medida: {vel:,.0f} intentos/s\n"
                           f"Intentos esperados para este p: ~p/2 ≈ 10^{math.log10(esperado):.0f}\n"
                           f"Tiempo estimado en el peor caso típico: {tiempo}", True)

        tema.correr_en_hilo(
            self, lambda: aritmetica.log_discreto_fuerza_bruta(g, A, p, maximo), listo,
            lambda e: (self._escribir(f"⚠ {e}"), self.btn.configure(state="normal", text="Intentar romper")))
