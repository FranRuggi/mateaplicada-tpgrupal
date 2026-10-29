"""Entrada a salas por Internet y elección de personaje reservada en el servidor."""
from pathlib import Path
import queue
import tkinter as tk

import customtkinter as ctk

from gui import tema
from gui.vistas.partida_red import VistaPartidaRed
from protocolo.sesion import ErrorProtocolo
from transporte.canal import ErrorCanal
from transporte.internet import ClienteSalas, url_predeterminada


class VistaInternet(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.cliente = None
        self.partida = None
        self.estado = None
        self._intencion = None
        self._sondeo = None
        self.lobby = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.lobby.grid(row=0, column=0, sticky="nsew")
        self.lobby.grid_columnconfigure((0, 2), weight=1)
        self.lobby.grid_columnconfigure(1, weight=4)
        centro = ctk.CTkFrame(self.lobby, fg_color="transparent")
        centro.grid(row=0, column=1, sticky="ew", pady=20)
        centro.grid_columnconfigure((0, 1), weight=1, uniform="roles")
        ctk.CTkLabel(centro, text="SALA DE INTERCAMBIO", font=tema.fuente_mono(24),
                     anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew")
        ctk.CTkLabel(centro, text="Dos participantes · Alice y Bob · Eve escucha el canal",
                     font=tema.fuente(13), text_color=tema.TENUE, anchor="w").grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(2, 18))
        config = ctk.CTkFrame(centro, fg_color=tema.PANEL, corner_radius=12)
        config.grid(row=2, column=0, columnspan=2, sticky="ew")
        config.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(config, text="Servidor de salas", font=tema.fuente(12), anchor="w").grid(
            row=0, column=0, columnspan=3, sticky="ew", padx=14, pady=(10, 3))
        self.entrada_servidor = ctk.CTkEntry(config, placeholder_text="https://tu-servicio.onrender.com", height=32)
        self.entrada_servidor.insert(0, url_predeterminada())
        self.entrada_servidor.grid(row=1, column=0, columnspan=3, sticky="ew", padx=14)
        self.entrada_codigo = ctk.CTkEntry(config, placeholder_text="Código de 8 caracteres", height=32)
        self.entrada_codigo.grid(row=2, column=0, sticky="ew", padx=(14, 6), pady=12)
        self.btn_unir = ctk.CTkButton(config, text="Entrar a sala", width=115, height=32,
                                      command=lambda: self.conectar("unir"))
        self.btn_unir.grid(row=2, column=1, padx=(0, 6))
        self.btn_crear = ctk.CTkButton(config, text="Crear sala", width=115, height=32,
                                       fg_color=tema.BOB, text_color="#0b0f18",
                                       command=lambda: self.conectar("crear"))
        self.btn_crear.grid(row=2, column=2, padx=(0, 14))
        fila_sala = ctk.CTkFrame(centro, fg_color="transparent")
        fila_sala.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(14, 5))
        fila_sala.grid_columnconfigure(0, weight=1)
        self.lbl_sala = ctk.CTkLabel(fila_sala, text="Elegí o creá una sala", font=tema.fuente(17, "bold"), anchor="w")
        self.lbl_sala.grid(row=0, column=0, sticky="w")
        self.btn_copiar = ctk.CTkButton(fila_sala, text="Copiar código", width=110, height=28,
                                        fg_color=tema.PANEL_2, command=self._copiar_codigo)
        self.btn_copiar.grid(row=0, column=1, padx=6)
        self.btn_salir = ctk.CTkButton(fila_sala, text="Salir", width=75, height=28,
                                       fg_color=tema.PANEL_2, command=self.salir)
        self.btn_salir.grid(row=0, column=2)

        ruta = Path(__file__).resolve().parents[2] / "assets" / "personajes-arcade.png"
        hoja = tk.PhotoImage(master=self, file=str(ruta))
        celda = hoja.width()//3
        self.botones_rol, self.lbl_roles, self._imagenes = {}, {}, []
        for i, (rol, indice, color, descripcion) in enumerate([
            ("Alice", 0, tema.ALICE, "Publica p y g · Elige a"),
            ("Bob", 2, tema.BOB, "Recibe p y g · Elige b"),
        ]):
            tarjeta = ctk.CTkFrame(centro, fg_color=tema.PANEL, corner_radius=14,
                                     border_width=1, border_color=color)
            tarjeta.grid(row=4, column=i, sticky="nsew", padx=(0, 8) if i == 0 else (8, 0), pady=8)
            tarjeta.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(tarjeta, text=rol.upper(), font=tema.fuente_mono(20), text_color=color).grid(
                row=0, column=0, pady=(14, 3))
            imagen = tk.PhotoImage(master=self)
            imagen.tk.call(imagen, "copy", hoja, "-from", indice*celda, 0,
                            (indice+1)*celda, hoja.height(), "-subsample", 4, 4)
            self._imagenes.append(imagen)
            tk.Label(tarjeta, image=imagen, bd=0, bg=tema.PANEL).grid(row=1, column=0, pady=6)
            ctk.CTkLabel(tarjeta, text=descripcion, font=tema.fuente(12),
                         text_color=tema.TENUE).grid(row=2, column=0)
            self.lbl_roles[rol] = ctk.CTkLabel(tarjeta, text="Esperando sala", font=tema.fuente(12, "bold"))
            self.lbl_roles[rol].grid(row=3, column=0, pady=(7, 4))
            boton = ctk.CTkButton(tarjeta, text=f"Elegir {rol}", fg_color=color,
                                   text_color="#0b0f18", height=34,
                                   command=lambda r=rol: self.elegir(r))
            boton.grid(row=4, column=0, sticky="ew", padx=16, pady=(2, 16))
            self.botones_rol[rol] = boton
        self.lbl_estado = ctk.CTkLabel(centro, text="Creá una sala y compartí el código con la otra persona.",
                                       font=tema.fuente(12), text_color=tema.TENUE,
                                       wraplength=650, justify="left", anchor="w")
        self.lbl_estado.grid(row=5, column=0, columnspan=2, sticky="ew", pady=8)
        self._actualizar_controles()

    def conectar(self, accion):
        if self.cliente:
            return
        codigo = self.entrada_codigo.get().strip().upper()
        if accion == "unir" and len(codigo) != 8:
            self.lbl_estado.configure(text="Ingresá el código de 8 caracteres de la sala.", text_color=tema.EVE)
            return
        try:
            self.cliente = ClienteSalas(self.entrada_servidor.get())
        except ValueError as e:
            self.lbl_estado.configure(text=str(e), text_color=tema.EVE)
            return
        self._intencion = (accion, codigo)
        self.lbl_estado.configure(text="Conectando con el servidor…", text_color=tema.TENUE)
        self.cliente.conectar()
        self._actualizar_controles()
        self._sondeo = self.after(40, self._sondear)

    def elegir(self, rol):
        if self.cliente:
            try:
                self.cliente.enviar("elegir", rol=rol)
            except ErrorCanal as e:
                self.lbl_estado.configure(text=str(e), text_color=tema.EVE)

    def _sondear(self):
        self._sondeo = None
        cliente = self.cliente
        if cliente is None:
            return
        for _ in range(100):
            try:
                evento = cliente.eventos.get_nowait()
            except queue.Empty:
                break
            try:
                self._manejar_evento(evento)
            except (ErrorCanal, ErrorProtocolo, ValueError, TypeError, KeyError) as e:
                self.salir(mensaje=f"El intercambio se interrumpió: {e}")
                break
            if self.cliente is not cliente:
                break
        if self.cliente:
            self._sondeo = self.after(40, self._sondear)

    def _manejar_evento(self, evento):
        tipo = evento.get("evento")
        if tipo == "conectado":
            accion, codigo = self._intencion
            self.cliente.enviar(accion, **({"sala": codigo} if accion == "unir" else {}))
        elif tipo == "conectando":
            self.lbl_estado.configure(text=evento["mensaje"], text_color=tema.TENUE)
        elif tipo == "bienvenida":
            if evento.get("protocolo") != 1:
                raise ValueError("La versión del servidor no es compatible.")
        elif tipo == "estado":
            self.estado = evento
            if evento.get("sala"):
                self.lbl_sala.configure(text=f"SALA {evento['sala']}")
                self.lbl_estado.configure(text="Elegí tu personaje." if not evento.get("rol")
                                           else "Tu personaje está reservado. Esperando a la otra persona…",
                                           text_color=tema.TENUE)
            nueva = evento.get("partida")
            if self.partida and self.partida.partida != nueva:
                self.partida.destroy()
                self.partida = None
                self.lobby.grid(row=0, column=0, sticky="nsew")
                self.lbl_estado.configure(text="La otra persona salió. Tu personaje sigue reservado.", text_color=tema.AVISO)
            if nueva and self.partida is None:
                if evento.get("rol") not in ("Alice", "Bob"):
                    raise ValueError("El servidor no asignó un personaje válido.")
                self.partida = VistaPartidaRed(self, self.cliente, evento["sala"], evento["rol"], nueva, self.salir)
                self.lobby.grid_forget()
                self.partida.grid(row=0, column=0, sticky="nsew")
            self._actualizar_controles()
        elif tipo == "mensaje":
            if self.partida:
                self.partida.aplicar_mensaje(evento)
        elif tipo == "error":
            texto = str(evento.get("mensaje", "Error del servidor"))
            if self.partida:
                self.partida.mostrar_error(texto)
            else:
                self.lbl_estado.configure(text=texto, text_color=tema.EVE)
                if not self.estado or not self.estado.get("sala"):
                    self.salir(mensaje=texto)
        elif tipo == "desconectado":
            self.salir(mensaje=evento.get("mensaje", "Se perdió la conexión."))

    def _actualizar_controles(self):
        conectado = self.cliente is not None
        for control in (self.entrada_servidor, self.entrada_codigo, self.btn_crear, self.btn_unir):
            control.configure(state="disabled" if conectado else "normal")
        self.btn_salir.configure(state="normal" if conectado else "disabled")
        en_sala = bool(self.estado and self.estado.get("sala"))
        self.btn_copiar.configure(state="normal" if en_sala else "disabled")
        propio = self.estado.get("rol") if en_sala else None
        roles = self.estado.get("roles", {}) if en_sala else {}
        for rol, boton in self.botones_rol.items():
            ocupado = bool(roles.get(rol))
            self.lbl_roles[rol].configure(text="Elegido por vos" if propio == rol else
                                          "Ocupado" if ocupado else "Disponible" if en_sala else "Esperando sala",
                                          text_color=tema.TENUE if ocupado and propio != rol else tema.TEXTO)
            boton.configure(state="normal" if en_sala and not propio and not ocupado else "disabled")

    def _copiar_codigo(self):
        if self.estado and self.estado.get("sala"):
            self.clipboard_clear()
            self.clipboard_append(self.estado["sala"])

    def salir(self, mensaje="Saliste de la sala."):
        if self._sondeo:
            self.after_cancel(self._sondeo)
            self._sondeo = None
        if self.cliente:
            self.cliente.cerrar()
            self.cliente = None
        if self.partida:
            self.partida.destroy()
            self.partida = None
        self.estado = None
        self.lobby.grid(row=0, column=0, sticky="nsew")
        self.lbl_sala.configure(text="Elegí o creá una sala")
        self.lbl_estado.configure(text=mensaje, text_color=tema.TENUE)
        self._actualizar_controles()

    def datos_para_eve(self):
        return self.partida.datos_para_eve() if self.partida else {}

    def destroy(self):
        self.salir()
        super().destroy()
