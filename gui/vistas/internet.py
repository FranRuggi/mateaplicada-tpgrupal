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
        self.grid_rowconfigure(1, weight=1)
        self.cliente = None
        self.partida = None
        self.estado = None
        self._intencion = None
        self._sondeo = None
        progreso = ctk.CTkFrame(self, fg_color="transparent")
        progreso.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        progreso.grid_columnconfigure((0, 1, 2), weight=1, uniform="pasos")
        self.indicadores_paso = {}
        for i, (paso, texto) in enumerate((("sala", "1 · Sala"),
                                            ("personaje", "2 · Personaje"),
                                            ("partida", "3 · Partida"))):
            indicador = ctk.CTkLabel(progreso, text=texto, height=30, corner_radius=8,
                                      font=tema.fuente(12, "bold"))
            indicador.grid(row=0, column=i, sticky="ew", padx=(0, 6) if i < 2 else 0)
            self.indicadores_paso[paso] = indicador
        self.lobby = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.lobby.grid(row=1, column=0, sticky="nsew")
        self.lobby.grid_columnconfigure((0, 2), weight=1)
        self.lobby.grid_columnconfigure(1, weight=4)
        centro = ctk.CTkFrame(self.lobby, fg_color="transparent")
        centro.grid(row=0, column=1, sticky="ew", pady=20)
        centro.grid_columnconfigure((0, 1), weight=1, uniform="roles")
        self.lbl_titulo = ctk.CTkLabel(centro, text="", font=tema.fuente_mono(24), anchor="w")
        self.lbl_titulo.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.lbl_subtitulo = ctk.CTkLabel(centro, text="", font=tema.fuente(13),
                                          text_color=tema.TENUE, anchor="w")
        self.lbl_subtitulo.grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(2, 18))
        self.paso_sala = ctk.CTkFrame(centro, fg_color="transparent")
        self.paso_sala.grid_columnconfigure((0, 1), weight=1, uniform="acceso")
        config = ctk.CTkFrame(self.paso_sala, fg_color=tema.PANEL, corner_radius=12)
        config.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        config.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(config, text="Servidor de salas", font=tema.fuente(12), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=14, pady=(10, 3))
        self.entrada_servidor = ctk.CTkEntry(config, placeholder_text="https://tu-servicio.onrender.com", height=32)
        self.entrada_servidor.insert(0, url_predeterminada())
        self.entrada_servidor.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        crear = ctk.CTkFrame(self.paso_sala, fg_color=tema.PANEL, corner_radius=14)
        crear.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        crear.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(crear, text="Crear una sala", font=tema.fuente(18, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(16, 4))
        ctk.CTkLabel(crear, text="Empezá una partida y compartí el código con la otra persona.",
                     wraplength=290, justify="left", anchor="w", text_color=tema.TENUE).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.btn_crear = ctk.CTkButton(crear, text="Crear sala", height=34,
                                       fg_color=tema.BOB, text_color="#0b0f18",
                                       command=lambda: self.conectar("crear"))
        self.btn_crear.grid(row=3, column=0, sticky="ew", padx=16, pady=(8, 16))
        crear.grid_rowconfigure(2, weight=1)
        entrar = ctk.CTkFrame(self.paso_sala, fg_color=tema.PANEL, corner_radius=14)
        entrar.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        entrar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(entrar, text="Entrar con un código", font=tema.fuente(18, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(16, 4))
        ctk.CTkLabel(entrar, text="Usá el código que te compartió la otra persona.",
                     wraplength=290, justify="left", anchor="w", text_color=tema.TENUE).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.entrada_codigo = ctk.CTkEntry(entrar, placeholder_text="Código de 8 caracteres", height=32)
        self.entrada_codigo.grid(row=2, column=0, sticky="ew", padx=16)
        self.btn_unir = ctk.CTkButton(entrar, text="Entrar a sala", height=34,
                                      command=lambda: self.conectar("unir"))
        self.btn_unir.grid(row=3, column=0, sticky="ew", padx=16, pady=(8, 16))
        self.btn_cancelar = ctk.CTkButton(self.paso_sala, text="Cancelar conexión", width=150,
                                          fg_color=tema.PANEL_2, command=self.salir)
        self.btn_cancelar.grid(row=2, column=0, columnspan=2, pady=(14, 0))

        self.paso_personaje = ctk.CTkFrame(centro, fg_color="transparent")
        self.paso_personaje.grid_columnconfigure((0, 1), weight=1, uniform="roles")
        fila_sala = ctk.CTkFrame(self.paso_personaje, fg_color="transparent")
        fila_sala.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        fila_sala.grid_columnconfigure(0, weight=1)
        self.lbl_sala = ctk.CTkLabel(fila_sala, text="", font=tema.fuente(17, "bold"), anchor="w")
        self.lbl_sala.grid(row=0, column=0, sticky="w")
        self.btn_copiar = ctk.CTkButton(fila_sala, text="Copiar código", width=110, height=28,
                                        fg_color=tema.PANEL_2, command=self._copiar_codigo)
        self.btn_copiar.grid(row=0, column=1, padx=6)
        self.btn_salir = ctk.CTkButton(fila_sala, text="Salir de la sala", width=120, height=28,
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
            tarjeta = ctk.CTkFrame(self.paso_personaje, fg_color=tema.PANEL, corner_radius=14,
                                     border_width=1, border_color=color)
            tarjeta.grid(row=1, column=i, sticky="nsew", padx=(0, 8) if i == 0 else (8, 0), pady=8)
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
        self.lbl_estado = ctk.CTkLabel(centro, text="Primero creá una sala o ingresá con un código.",
                                       font=tema.fuente(12), text_color=tema.TENUE,
                                       wraplength=650, justify="left", anchor="w")
        self.lbl_estado.grid(row=3, column=0, columnspan=2, sticky="ew", pady=8)
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
        if self.cliente and self.estado and self.estado.get("sala") and not self.partida:
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
                                           else f"Elegiste {evento['rol']}. Esperando a la otra persona para jugar…",
                                           text_color=tema.TENUE)
            nueva = evento.get("partida")
            if self.partida and self.partida.partida != nueva:
                self.partida.destroy()
                self.partida = None
                self.lbl_estado.configure(text="La otra persona salió. Tu personaje sigue reservado.", text_color=tema.AVISO)
            if nueva and self.partida is None:
                if evento.get("rol") not in ("Alice", "Bob"):
                    raise ValueError("El servidor no asignó un personaje válido.")
                self.partida = VistaPartidaRed(self, self.cliente, evento["sala"], evento["rol"], nueva, self.salir)
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
        if conectado and not en_sala:
            self.btn_cancelar.grid()
        else:
            self.btn_cancelar.grid_remove()
        self.btn_copiar.configure(state="normal" if en_sala else "disabled")
        propio = self.estado.get("rol") if en_sala else None
        roles = self.estado.get("roles", {}) if en_sala else {}
        for rol, boton in self.botones_rol.items():
            ocupado = bool(roles.get(rol))
            self.lbl_roles[rol].configure(text="Elegido por vos" if propio == rol else
                                          "Ocupado" if ocupado else "Disponible" if en_sala else "Esperando sala",
                                          text_color=tema.TENUE if ocupado and propio != rol else tema.TEXTO)
            boton.configure(state="normal" if en_sala and not propio and not ocupado else "disabled")
        self._mostrar_paso("partida" if self.partida else "personaje" if en_sala else "sala")

    def _mostrar_paso(self, paso):
        self.paso_actual = paso
        for nombre, indicador in self.indicadores_paso.items():
            indicador.configure(fg_color=tema.ALICE if nombre == paso else tema.PANEL,
                                  text_color=tema.TEXTO if nombre == paso else tema.TENUE)
        if paso == "partida":
            self.lobby.grid_remove()
            self.partida.grid(row=1, column=0, sticky="nsew")
            return
        self.lobby.grid(row=1, column=0, sticky="nsew")
        self.paso_sala.grid_remove()
        self.paso_personaje.grid_remove()
        if paso == "sala":
            self.lbl_titulo.configure(text="CREÁ O ENTRÁ A UNA SALA")
            self.lbl_subtitulo.configure(text="Primero compartan una sala. Después van a elegir sus personajes.")
            self.paso_sala.grid(row=2, column=0, columnspan=2, sticky="ew")
        else:
            self.lbl_titulo.configure(text="ELEGÍ TU PERSONAJE")
            self.lbl_subtitulo.configure(text="Una persona juega como Alice y la otra como Bob. Eve escucha el canal.")
            self.paso_personaje.grid(row=2, column=0, columnspan=2, sticky="ew")

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
        self.lbl_sala.configure(text="")
        self.lbl_estado.configure(text=mensaje, text_color=tema.TENUE)
        self._actualizar_controles()

    def datos_para_eve(self):
        return self.partida.datos_para_eve() if self.partida else {}

    def destroy(self):
        self.salir()
        super().destroy()
