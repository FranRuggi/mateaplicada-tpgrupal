"""Área de trabajo con consola acoplable y separador nativo de Tk."""
import tkinter as tk

import customtkinter as ctk

from gui import tema
from gui.componentes import PanelPasos


class AreaConRegistro(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._ubicacion = "Abajo"
        self._tamanos = {"Abajo": 260, "Derecha": 380}
        self._expandido = False
        self._ajuste_id = None
        self._guardar_id = None

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        barra.grid_columnconfigure(0, weight=1)
        self.lbl_titulo = ctk.CTkLabel(barra, text="Modo local", font=tema.fuente(15, "bold"), anchor="w")
        self.lbl_titulo.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(barra, text="Consola", font=tema.fuente(12),
                     text_color=tema.TENUE).grid(row=0, column=1, padx=(10, 8))
        self.sel_ubicacion = ctk.CTkSegmentedButton(
            barra, values=["Abajo", "Derecha"], height=28,
            font=tema.fuente(12), command=self.colocar_registro)
        self.sel_ubicacion.set("Abajo")
        self.sel_ubicacion.grid(row=0, column=2)

        self.division = tk.PanedWindow(self, orient=tk.VERTICAL, bd=0,
                                       bg=tema.BORDE, sashwidth=10, sashpad=0,
                                       sashrelief="flat", showhandle=True,
                                       handlesize=8, handlepad=35, opaqueresize=True,
                                       sashcursor="sb_v_double_arrow")
        self.division.grid(row=1, column=0, sticky="nsew")
        self.panel_principal = ctk.CTkFrame(self.division, fg_color=tema.FONDO,
                                             corner_radius=0)
        self.panel_principal.grid_columnconfigure(0, weight=1)
        self.panel_principal.grid_rowconfigure(0, weight=1)
        self.cuerpo = ctk.CTkScrollableFrame(self.panel_principal, fg_color="transparent",
                                              corner_radius=0)
        self.cuerpo.grid(row=0, column=0, sticky="nsew")

        self.panel_registro = ctk.CTkFrame(self.division, fg_color=tema.PANEL,
                                            corner_radius=10)
        self.panel_registro.grid_columnconfigure(0, weight=1)
        self.panel_registro.grid_rowconfigure(1, weight=1)
        cab = ctk.CTkFrame(self.panel_registro, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 0))
        cab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cab, text="Consola y pasos", font=tema.fuente(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="w")
        self.btn_ampliar = ctk.CTkButton(cab, text="Ampliar", width=90, height=27,
                                         fg_color=tema.PANEL_2, command=self.ampliar_registro)
        self.btn_ampliar.grid(row=0, column=1, padx=(6, 0))
        self.registro = ctk.CTkTabview(self.panel_registro, height=160,
                                        fg_color=tema.PANEL, corner_radius=10)
        self.registro.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 5))
        consola = self.registro.add("Consola")
        detalle = self.registro.add("Paso a paso")
        for panel in (consola, detalle):
            panel.grid_columnconfigure(0, weight=1)
            panel.grid_rowconfigure(0, weight=1)
        self.consola = ctk.CTkTextbox(consola, height=120, font=tema.fuente_mono(12),
                                      fg_color=tema.PANEL_2, wrap="word")
        self.consola.grid(row=0, column=0, sticky="nsew")
        self.pasos = PanelPasos(detalle, alto=120, compacto=True)
        self.pasos.grid(row=0, column=0, sticky="nsew")

        self.division.add(self.panel_principal, stretch="always")
        self.division.add(self.panel_registro, stretch="never")
        self.division.bind("<Configure>", lambda _e: self._programar_ajuste())
        self.division.bind("<ButtonRelease-1>", self._al_soltar_separador, add="+")
        self.colocar_registro("Abajo")

    def colocar_registro(self, ubicacion):
        if ubicacion not in self._tamanos:
            raise ValueError("La consola puede ubicarse Abajo o Derecha.")
        if not self._expandido:
            self._recordar_tamano()
        self._ubicacion = ubicacion
        self.sel_ubicacion.set(ubicacion)
        self._expandido = False
        self.btn_ampliar.configure(text="Ampliar")
        lateral = ubicacion == "Derecha"
        escala = self._get_widget_scaling()
        self.division.configure(orient=tk.HORIZONTAL if lateral else tk.VERTICAL,
                                sashcursor="sb_h_double_arrow" if lateral else "sb_v_double_arrow",
                                sashwidth=round(10*escala), handlesize=round(8*escala))
        self.division.paneconfigure(self.panel_principal, minsize=round((480 if lateral else 220)*escala))
        self.division.paneconfigure(self.panel_registro, minsize=round((300 if lateral else 180)*escala),
                                    width=round(self._tamanos["Derecha"]*escala),
                                    height=round(self._tamanos["Abajo"]*escala))
        self._programar_ajuste()

    def ampliar_registro(self):
        if not self._expandido:
            self._recordar_tamano()
        self._expandido = not self._expandido
        self.btn_ampliar.configure(text="Restaurar" if self._expandido else "Ampliar")
        self._programar_ajuste()

    def _programar_ajuste(self):
        if self._ajuste_id is None:
            self._ajuste_id = self.after_idle(self._aplicar_tamano)

    def _aplicar_tamano(self):
        self._ajuste_id = None
        escala = self._get_widget_scaling()
        lateral = self._ubicacion == "Derecha"
        total = self.division.winfo_width() if lateral else self.division.winfo_height()
        minimo_principal = round((480 if lateral else 220)*escala)
        minimo_registro = round((300 if lateral else 180)*escala)
        separador = round(10*escala)
        if total < minimo_principal+minimo_registro+separador:
            return  # Todavía no se mapeó la ventana.
        deseado = round(total*.7) if self._expandido else round(self._tamanos[self._ubicacion]*escala)
        tamano = min(max(minimo_registro, deseado), total-minimo_principal-separador)
        posicion = total-tamano-separador
        self.division.sash_place(0, posicion if lateral else 0, 0 if lateral else posicion)

    def _recordar_tamano(self):
        lateral = self._ubicacion == "Derecha"
        tamano = self.panel_registro.winfo_width() if lateral else self.panel_registro.winfo_height()
        if tamano > 1:
            self._tamanos[self._ubicacion] = tamano/self._get_widget_scaling()

    def _al_soltar_separador(self, _evento):
        if self._guardar_id is None:
            self._guardar_id = self.after_idle(self._guardar_arrastre)

    def _guardar_arrastre(self):
        self._guardar_id = None
        self._expandido = False
        self.btn_ampliar.configure(text="Ampliar")
        self._recordar_tamano()

    def destroy(self):
        for identificador in (self._ajuste_id, self._guardar_id):
            if identificador is not None:
                self.after_cancel(identificador)
        super().destroy()
