"""Pantalla de inicio: qué es DH, accesos a cada modo y estado de los módulos."""
import customtkinter as ctk

from core import aritmetica
from gui import tema
from gui.componentes import Tarjeta


class VistaInicio(ctk.CTkFrame):
    def __init__(self, master, navegar):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure((0, 1, 2), weight=1, uniform="c")

        ctk.CTkLabel(self, text="Intercambio de claves Diffie-Hellman", font=tema.fuente(28, "bold"),
                     anchor="w").grid(row=0, column=0, columnspan=3, sticky="ew")
        ctk.CTkLabel(self, text="Dos personas acuerdan una clave secreta hablando por un canal que "
                                "cualquiera puede escuchar.",
                     font=tema.fuente(14), text_color=tema.TENUE, anchor="w").grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(2, 18))

        formulas = [("Alice calcula", "A = gᵃ mod p", tema.ALICE),
                    ("Bob calcula", "B = gᵇ mod p", tema.BOB),
                    ("Ambos obtienen", "K = Bᵃ = Aᵇ = gᵃᵇ mod p", tema.OK)]
        for i, (t, f, c) in enumerate(formulas):
            caja = ctk.CTkFrame(self, fg_color=tema.PANEL, corner_radius=14, border_width=1, border_color=c)
            caja.grid(row=2, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))
            ctk.CTkLabel(caja, text=t, text_color=tema.TENUE, font=tema.fuente(12)).pack(pady=(14, 0))
            ctk.CTkLabel(caja, text=f, text_color=c, font=tema.fuente_mono(18)).pack(pady=(2, 14))

        accesos = [("Modo local", "Alice, Bob y Eve en la misma pantalla. Ideal para la demo y "
                                  "para explicar el protocolo paso a paso.", "local", tema.ALICE),
                   ("Modo red", "Cada computadora juega un rol. Intercambio por archivos .txt "
                                "o por sockets TCP.", "red", tema.BOB),
                   ("Ataque de Eve", "Intento de fuerza bruta del logaritmo discreto: por qué "
                                     "p tiene que ser grande.", "eve", tema.EVE)]
        for i, (titulo, desc, destino, color) in enumerate(accesos):
            t = Tarjeta(self, titulo, color=color)
            t.grid(row=3, column=i, sticky="nsew", pady=(16, 0),
                   padx=(0 if i == 0 else 6, 0 if i == 2 else 6))
            ctk.CTkLabel(t, text=desc, wraplength=300, justify="left", anchor="w",
                         text_color=tema.TENUE, font=tema.fuente(12)).grid(
                row=t.siguiente_fila, column=0, sticky="ew", padx=16, pady=(4, 10))
            ctk.CTkButton(t, text="Abrir →", fg_color=color, text_color="#0b0f18",
                          font=tema.fuente(13, "bold"), hover_color=tema.BORDE,
                          command=lambda d=destino: navegar(d)).grid(
                row=t.siguiente_fila + 1, column=0, sticky="w", padx=16, pady=(0, 14))

        estado = Tarjeta(self, "Estado de los módulos", "Se actualiza solo a medida que el grupo "
                                                       "reemplaza los mocks")
        estado.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        modulos = [
            ("core/aritmetica.py", "Motor matemático (mod_pow, primos, generador)",
             "MOCK · usa pow() de Python" if aritmetica.MOCK else "Implementado", not aritmetica.MOCK),
            ("protocolo/sesion.py", "Estados y validaciones de Alice / Bob", "Listo", True),
            ("transporte · CanalMemoria", "Modo local", "Listo", True),
            ("transporte · CanalArchivo", "Intercambio por .txt (obligatorio)", "Pendiente", False),
            ("transporte · CanalSocket", "Dos computadoras (secundario)", "Pendiente", False),
        ]
        for i, (archivo, desc, txt, ok) in enumerate(modulos):
            fila = estado.siguiente_fila + i
            ctk.CTkLabel(estado, text=archivo, font=tema.fuente_mono(12), anchor="w").grid(
                row=fila, column=0, sticky="w", padx=16, pady=3)
            ctk.CTkLabel(estado, text=desc, text_color=tema.TENUE, anchor="w").grid(
                row=fila, column=1, sticky="w", padx=16)
            ctk.CTkLabel(estado, text=("✔ " if ok else "● ") + txt, anchor="e",
                         text_color=tema.OK if ok else tema.AVISO, font=tema.fuente(12, "bold")).grid(
                row=fila, column=2, sticky="e", padx=16)
        estado.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(estado, height=8, fg_color="transparent").grid(row=fila + 1, column=0)
