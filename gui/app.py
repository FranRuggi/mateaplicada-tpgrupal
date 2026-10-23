"""Ventana principal: barra lateral + área de contenido con las vistas."""
import customtkinter as ctk

from core import aritmetica
from gui import tema
from gui.vistas.eve import VistaEve
from gui.vistas.inicio import VistaInicio
from gui.vistas.modo_local import VistaModoLocal
from gui.vistas.modo_red import VistaModoRed


class App(ctk.CTk):
    SECCIONES = [("inicio", "⌂   Inicio"), ("local", "⇄   Modo local"),
                 ("red", "⌁   Modo red"), ("eve", "👁   Ataque de Eve")]

    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=tema.FONDO)
        self.title("Diffie-Hellman · Matemática Aplicada")
        self.geometry("1360x860")
        self.minsize(1200, 760)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._barra_lateral()
        self.contenido = ctk.CTkFrame(self, fg_color="transparent")
        self.contenido.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.contenido.grid_columnconfigure(0, weight=1)
        self.contenido.grid_rowconfigure(0, weight=1)

        self.vistas = {
            "inicio": VistaInicio(self.contenido, self.mostrar),
            "local": VistaModoLocal(self.contenido, self._abrir_eve),
            "red": VistaModoRed(self.contenido),
            "eve": VistaEve(self.contenido),
        }
        self.mostrar("inicio")

    def _barra_lateral(self):
        barra = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color=tema.PANEL)
        barra.grid(row=0, column=0, sticky="ns")
        barra.grid_propagate(False)
        barra.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(barra, text="DH · Key Exchange", font=tema.fuente(17, "bold")).grid(
            row=0, column=0, padx=18, pady=(24, 0), sticky="w")
        ctk.CTkLabel(barra, text="Matemática Aplicada · UNLaM", font=tema.fuente(11),
                     text_color=tema.TENUE).grid(row=1, column=0, padx=18, pady=(0, 24), sticky="w")
        self.botones = {}
        for i, (clave, texto) in enumerate(self.SECCIONES):
            b = ctk.CTkButton(barra, text=texto, anchor="w", height=38, corner_radius=8,
                              font=tema.fuente(13), fg_color="transparent", hover_color=tema.PANEL_2,
                              text_color=tema.TEXTO, command=lambda c=clave: self.mostrar(c))
            b.grid(row=2 + i, column=0, sticky="ew", padx=10, pady=2)
            self.botones[clave] = b
        barra.grid_rowconfigure(10, weight=1)
        motor = "Motor: MOCK ⚠" if aritmetica.MOCK else "Motor: propio ✔"
        ctk.CTkLabel(barra, text=motor, font=tema.fuente(11, "bold"),
                     text_color=tema.AVISO if aritmetica.MOCK else tema.OK).grid(
            row=11, column=0, padx=18, pady=(0, 18), sticky="w")

    def mostrar(self, clave):
        for k, v in self.vistas.items():
            v.grid_forget()
            self.botones[k].configure(fg_color=tema.PANEL_2 if k == clave else "transparent")
        self.vistas[clave].grid(row=0, column=0, sticky="nsew")

    def _abrir_eve(self, datos):
        self.vistas["eve"].cargar(datos)
        self.mostrar("eve")
