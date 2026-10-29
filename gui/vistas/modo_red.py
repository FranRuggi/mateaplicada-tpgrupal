"""Modos de transporte: salas de Internet y la carpeta compartida existente."""
import customtkinter as ctk

from gui import tema
from gui.vistas.internet import VistaInternet
from gui.vistas.modo_archivo import VistaModoArchivo


class VistaModoRed(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.selector = ctk.CTkSegmentedButton(self, values=["Internet · salas", "Archivos .txt"],
                                                font=tema.fuente(12), command=self.mostrar)
        self.selector.grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.internet = VistaInternet(self)
        self.archivos = VistaModoArchivo(self)
        self.mostrar("Internet · salas")

    def mostrar(self, modo):
        self.modo = modo
        self.selector.set(modo)
        self.internet.grid_forget()
        self.archivos.grid_forget()
        vista = self.internet if modo == "Internet · salas" else self.archivos
        vista.grid(row=1, column=0, sticky="nsew")

    def datos_para_eve(self):
        vista = self.internet if self.modo == "Internet · salas" else self.archivos
        return vista.datos_para_eve()
