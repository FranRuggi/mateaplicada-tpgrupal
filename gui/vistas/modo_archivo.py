"""Modo red: una instancia por rol y una cola en una carpeta compartida.
Los sockets TCP quedan reservados para una ampliación posterior.
"""
from core import aritmetica
import customtkinter as ctk
from tkinter import filedialog
from uuid import uuid4

from gui import tema
from gui.componentes import PanelPasos, Tarjeta, TarjetaParticipante
from protocolo.sesion import ErrorProtocolo, Participante
from transporte.canal import CanalArchivo, ErrorCanal, Mensaje


class VistaModoArchivo(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=4, uniform="c")
        self.grid_columnconfigure(1, weight=5, uniform="c")
        self.grid_columnconfigure(2, weight=5, uniform="c")
        self.grid_rowconfigure(0, weight=1)
        self.canal = None
        self._sondeo = None
        self._generando = False
        self._ultimo_error = None
        self._publicos_eve: dict[str, int] = {}

        self._panel_config().grid(row=0, column=0, sticky="nsew")
        self.contenedor_tarjeta = ctk.CTkFrame(self, fg_color="transparent")
        self.contenedor_tarjeta.grid(row=0, column=1, sticky="nsew", padx=10)
        self.contenedor_tarjeta.grid_columnconfigure(0, weight=1)
        self.contenedor_tarjeta.grid_rowconfigure(0, weight=1)

        der = ctk.CTkFrame(self, fg_color="transparent")
        der.grid(row=0, column=2, sticky="nsew")
        der.grid_columnconfigure(0, weight=1)
        der.grid_rowconfigure((0, 1), weight=1)
        self._panel_registro(der).grid(row=0, column=0, sticky="nsew")
        self.pasos = PanelPasos(der)
        self.pasos.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        self._cambiar_rol("Alice")
        self._cambiar_transporte("Archivos .txt")

    # -- configuración -----------------------------------------------------------
    def _panel_config(self):
        t = ctk.CTkScrollableFrame(self, fg_color=tema.PANEL, corner_radius=14,
                                   border_width=1, border_color=tema.BORDE)
        t.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(t, text="Conexión", font=tema.fuente(15, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        ctk.CTkLabel(t, text="Una instancia para Alice y otra para Bob",
                     font=tema.fuente(11), text_color=tema.TENUE, wraplength=240,
                     justify="left", anchor="w").grid(row=1, column=0, sticky="ew", padx=16)
        f = 2
        ctk.CTkLabel(t, text="Soy", font=tema.fuente(12, "bold"), text_color=tema.TENUE,
                     anchor="w").grid(row=f, column=0, sticky="ew", padx=16, pady=(10, 4))
        self.sel_rol = ctk.CTkSegmentedButton(t, values=["Alice", "Bob"], command=self._cambiar_rol)
        self.sel_rol.set("Alice")
        self.sel_rol.grid(row=f + 1, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(t, text="Transporte", font=tema.fuente(12, "bold"), text_color=tema.TENUE,
                     anchor="w").grid(row=f + 2, column=0, sticky="ew", padx=16, pady=(14, 4))
        self.sel_tr = ctk.CTkSegmentedButton(t, values=["Archivos .txt", "Sockets TCP"],
                                             command=self._cambiar_transporte)
        self.sel_tr.set("Archivos .txt")
        self.sel_tr.grid(row=f + 3, column=0, sticky="ew", padx=16)

        # opciones por archivo
        self.op_archivo = ctk.CTkFrame(t, fg_color="transparent")
        self.op_archivo.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.op_archivo, text="Carpeta compartida", font=tema.fuente(11),
                     text_color=tema.TENUE, anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew")
        self.entrada_carpeta = ctk.CTkEntry(self.op_archivo, placeholder_text="ej. Z:/intercambio")
        self.entrada_carpeta.grid(row=1, column=0, sticky="ew")
        self.btn_carpeta = ctk.CTkButton(self.op_archivo, text="Elegir…", width=70,
                                        fg_color=tema.PANEL_2, hover_color=tema.BORDE,
                                        command=self._elegir_carpeta)
        self.btn_carpeta.grid(row=1, column=1, padx=(6, 0))
        ctk.CTkLabel(self.op_archivo, text="Sesión (mismo código en ambos)",
                     font=tema.fuente(11), text_color=tema.TENUE, anchor="w").grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(10, 2))
        self.entrada_sesion = ctk.CTkEntry(self.op_archivo, placeholder_text="ej. grupo-1")
        self.entrada_sesion.insert(0, "demo")
        self.entrada_sesion.grid(row=3, column=0, sticky="ew")
        self.btn_sesion = ctk.CTkButton(self.op_archivo, text="Nuevo", width=70,
                                       fg_color=tema.PANEL_2, hover_color=tema.BORDE,
                                       command=self._nueva_sesion)
        self.btn_sesion.grid(row=3, column=1, padx=(6, 0))

        # opciones por socket
        self.op_socket = ctk.CTkFrame(t, fg_color="transparent")
        self.op_socket.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.op_socket, text="IP de la otra computadora / puerto", font=tema.fuente(11),
                     text_color=tema.TENUE, anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew")
        self.entrada_host = ctk.CTkEntry(self.op_socket, placeholder_text="192.168.0.15")
        self.entrada_host.grid(row=1, column=0, sticky="ew")
        self.entrada_puerto = ctk.CTkEntry(self.op_socket, width=70)
        self.entrada_puerto.insert(0, "5000")
        self.entrada_puerto.grid(row=1, column=1, padx=(6, 0))
        self.lbl_srv = ctk.CTkLabel(self.op_socket, text="", font=tema.fuente(11), text_color=tema.TENUE,
                                    anchor="w", justify="left", wraplength=240)
        self.lbl_srv.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.fila_opciones = f + 4

        # --- SECCIÓN DE PARÁMETROS PÚBLICOS (Fila f + 5) ---
        self.frame_params = ctk.CTkFrame(t, fg_color="transparent")
        self.frame_params.grid(row=f + 5, column=0, sticky="ew", padx=16, pady=(12, 0))
        self.frame_params.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_params, text="p y g (solo Alice):", font=tema.fuente(11, "bold"), text_color=tema.TENUE).grid(row=0, column=0, sticky="w", columnspan=2, pady=(0, 2))

        self.entrada_p_red = ctk.CTkEntry(self.frame_params, placeholder_text="p", font=tema.fuente_mono(10), height=28)
        self.entrada_p_red.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=2)

        self.entrada_g_red = ctk.CTkEntry(self.frame_params, placeholder_text="g", font=tema.fuente_mono(10), width=50, height=28)
        self.entrada_g_red.grid(row=1, column=1, sticky="ew", pady=2)

        self.btn_gen_red = ctk.CTkButton(self.frame_params, text="Generar p y g", height=26, command=self._generar_params_red)
        self.btn_gen_red.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)

        self.btn_pub_red = ctk.CTkButton(self.frame_params, text="Publicar p y g al canal", height=26, fg_color=tema.ALICE, text_color="#0b0f18", command=self._publicar_params_red)
        self.btn_pub_red.grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)

        # Botón de conexión y estados (Filas f + 6, f + 7, f + 8)
        botones = ctk.CTkFrame(t, fg_color="transparent")
        botones.grid(row=f + 6, column=0, sticky="ew", padx=16, pady=(14, 6))
        botones.grid_columnconfigure((0, 1), weight=1)
        self.btn_conectar = ctk.CTkButton(botones, text="Conectar", width=100, height=32,
                                         command=self._conectar)
        self.btn_conectar.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.btn_desconectar = ctk.CTkButton(botones, text="Desconectar", width=100, height=32,
                                            fg_color=tema.PANEL_2, command=self._desconectar)
        self.btn_desconectar.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.lbl_estado = ctk.CTkLabel(t, text="● Desconectado", text_color=tema.TENUE,
                                       font=tema.fuente(12), anchor="w", justify="left", wraplength=250)
        self.lbl_estado.grid(row=f + 7, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(t, text="Usen la misma carpeta y sesión.\nAlice publica p y g primero.\n"
                            "La recepción es automática.\nPara otro intercambio, usen otra sesión.",
                     font=tema.fuente(11), text_color=tema.TENUE, justify="left", anchor="w",
                     wraplength=240).grid(
            row=f + 8, column=0, sticky="ew", padx=16, pady=(12, 12))
        # --- BOTÓN DE RECEPCIÓN (Para Bob o Alice) ---
        self.btn_recibir = ctk.CTkButton(t, text="📥 Buscar mensajes nuevos", height=28,
                                         fg_color=tema.PANEL_2, text_color=tema.TEXTO,
                                         border_width=1, border_color=tema.BORDE,
                                         command=self._verificar_mensajes)
        self.btn_recibir.grid(row=f + 9, column=0, sticky="ew", padx=16, pady=(8, 12))
        return t
    def _generar_params_red(self):
        if self.yo.nombre != "Alice" or self._generando or self.yo.p is not None:
            return
        self._generando = True
        self.btn_gen_red.configure(text="Generando…")
        self._actualizar_controles()

        def listo(res):
            self._generando = False
            p, g, pasos = res
            self._poner_parametros(p, g)
            self.pasos.mostrar("Generación de p y g (64 bits)", pasos)
            self.btn_gen_red.configure(text="Generar p y g")
            self._actualizar_controles()

        def fallo(error):
            self._generando = False
            self.btn_gen_red.configure(text="Generar p y g")
            self._actualizar_controles()
            self._mostrar_error(str(error))

        tema.correr_en_hilo(self, lambda: aritmetica.generar_parametros(64), listo, fallo)

    def _poner_parametros(self, p, g):
        for entrada, valor in ((self.entrada_p_red, p), (self.entrada_g_red, g)):
            entrada.configure(state="normal")
            entrada.delete(0, "end")
            entrada.insert(0, str(valor))

    def _verificar_mensajes(self, manual=True):
        if self.canal is None:
            if manual:
                self._mostrar_error("Primero conectá la carpeta compartida.")
            return
        recibidos, hubo_error, esperando = 0, False, False
        # Limitar el lote para devolver el control a la interfaz entre sondeos.
        for _ in range(20):
            try:
                mensaje = self.canal.recibir(self.yo.nombre)
                if mensaje is None:
                    break
                if mensaje.tipo == "PUBLICA" and self.yo.p is None:
                    self.canal.posponer(mensaje)
                    esperando = True
                    break
                try:
                    self._procesar_mensaje(mensaje)
                except (ErrorProtocolo, ValueError) as e:
                    self.canal.rechazar(mensaje)
                    self._mostrar_error(f"Mensaje apartado en 'rechazados': {e}")
                    hubo_error = True
                    continue
                self.canal.confirmar(mensaje)
                self._log(f"Recibido y procesado:\n{mensaje.a_texto()}")
                recibidos += 1
            except ErrorCanal as e:
                self._mostrar_error(str(e))
                hubo_error = True
            except OSError as e:
                self._mostrar_error(f"No se pudo acceder a la carpeta: {e}")
                hubo_error = True
                break
        self.tarjeta.refrescar()
        self._actualizar_controles()
        if not hubo_error:
            self._ultimo_error = None
            texto = "Esperando los parámetros de Alice…" if esperando else "Recepción automática activa"
            self.lbl_estado.configure(text=f"● Conectado · {texto}", text_color=tema.OK)
            if manual and not recibidos and not esperando:
                self._log("No hay mensajes pendientes.")

    def _procesar_mensaje(self, mensaje):
        if mensaje.tipo == "PARAMETROS":
            p, g = mensaje.datos["p"], mensaje.datos["g"]
            if self.yo.p is None:
                self.yo.establecer_parametros(p, g)
            elif (self.yo.p, self.yo.g) != (p, g):
                raise ErrorProtocolo("Los parámetros cambiaron. Desconectá y usá otra sesión.")
            # Una retransmisión idéntica no borra claves ya calculadas.
            self._poner_parametros(p, g)
        else:
            clave = "A" if mensaje.remitente == "Alice" else "B"
            self.yo.recibir_publica(mensaje.datos[clave])
        self._publicos_eve.update(mensaje.datos)

    def _publicar_params_red(self):
        try:
            if self.canal is None:
                raise ErrorProtocolo("Primero conectá la carpeta compartida.")
            if self.yo.nombre != "Alice":
                raise ErrorProtocolo("Alice es quien publica los parámetros.")
            p = int(self.entrada_p_red.get())
            g = int(self.entrada_g_red.get())
            if self.yo.p is not None and (self.yo.p, self.yo.g) != (p, g):
                raise ErrorProtocolo("Para cambiar los parámetros, desconectá y usá otra sesión.")
            candidato = Participante("Alice")
            candidato.establecer_parametros(p, g)
            m = Mensaje("Alice", "Bob", "PARAMETROS", {"p": p, "g": g})
            self.canal.enviar(m)
            if self.yo.p is None:
                self.yo.establecer_parametros(p, g)
            self._publicos_eve.update(m.datos)
            self.tarjeta.refrescar()
            self._actualizar_controles()
            self._log(f"Enviado:\n{m.a_texto()}")
        except (ErrorProtocolo, ErrorCanal, OSError) as e:
            self._mostrar_error(str(e))
        except ValueError:
            self._mostrar_error("p y g deben ser números enteros válidos.")

    def _panel_registro(self, master):
        t = Tarjeta(master, "Mensajes en texto plano", "Datos públicos enviados y recibidos")
        self.registro = ctk.CTkTextbox(t, font=tema.fuente_mono(12), fg_color=tema.PANEL_2,
                                       corner_radius=10)
        self.registro.grid(row=t.siguiente_fila, column=0, sticky="nsew", padx=12, pady=(4, 12))
        t.grid_rowconfigure(t.siguiente_fila, weight=1)
        ejemplo = Mensaje("Alice", "Bob", "PUBLICA", {"A": 1234567})
        self._log(f"# Contenido de ejemplo: cada envío crea un archivo distinto.\n{ejemplo.a_texto()}")
        return t

    # -- eventos ------------------------------------------------------------------
    def _cambiar_rol(self, rol):
        self._desconectar(avisar=False)
        self.sel_rol.set(rol)
        for w in self.contenedor_tarjeta.winfo_children():
            w.destroy()
        self.yo = Participante(rol)
        es_alice = rol == "Alice"
        tarjeta = TarjetaParticipante(
            self.contenedor_tarjeta, self.yo, tema.ALICE if es_alice else tema.BOB,
            "Bob" if es_alice else "Alice", "a" if es_alice else "b",
            "A" if es_alice else "B", "B" if es_alice else "A",
            self._enviar, self.pasos.mostrar if hasattr(self, "pasos") else lambda *_: None)
        tarjeta.grid(row=0, column=0, sticky="nsew")
        self.tarjeta = tarjeta
        if hasattr(self, "lbl_srv"):
            self._texto_servidor()
        self._actualizar_controles()

    def _cambiar_transporte(self, valor):
        self._desconectar(avisar=False)
        self.op_archivo.grid_forget(); self.op_socket.grid_forget()
        opc = self.op_archivo if valor.startswith("Archivos") else self.op_socket
        opc.grid(row=self.fila_opciones, column=0, sticky="ew", padx=16, pady=(12, 0))
        self._texto_servidor()

    def _texto_servidor(self):
        if self.sel_rol.get() == "Bob":
            self.lbl_srv.configure(text="Bob escucha (servidor) en el puerto indicado.")
        else:
            self.lbl_srv.configure(text="Alice se conecta (cliente) a la IP de Bob.")

    def _elegir_carpeta(self):
        carpeta = filedialog.askdirectory()
        if carpeta:
            self.entrada_carpeta.delete(0, "end")
            self.entrada_carpeta.insert(0, carpeta)

    def _conectar(self):
        if self.canal is not None:
            return
        try:
            if self.sel_tr.get().startswith("Archivos"):
                canal = CanalArchivo(self.entrada_carpeta.get(), self.entrada_sesion.get().strip())
            else:
                raise ErrorProtocolo("Sockets TCP está pendiente. Usá 'Archivos .txt'.")
            self.canal = canal
            self.yo.reiniciar()
            self.tarjeta.refrescar()
            self._ultimo_error = None
            self.lbl_estado.configure(text="● Conectado · recepción automática", text_color=tema.OK)
            self._log(f"Conectado como {self.yo.nombre}. Sesión: {canal.sesion}\nCarpeta: {canal.carpeta}")
            self._actualizar_controles()
            self._sondeo = self.after(500, self._sondear)
        except (ErrorProtocolo, ErrorCanal, OSError, ValueError) as e:
            self._mostrar_error(str(e))

    def _sondear(self):
        self._sondeo = None
        try:
            self._verificar_mensajes(manual=False)
        finally:
            if self.canal is not None and self.winfo_exists():
                self._sondeo = self.after(500, self._sondear)

    def _desconectar(self, avisar=True):
        conectado = self.canal is not None
        if self._sondeo is not None:
            self.after_cancel(self._sondeo)
            self._sondeo = None
        self.canal = None
        self._publicos_eve.clear()
        self._ultimo_error = None
        if hasattr(self, "yo"):
            self.yo.reiniciar()
            self.tarjeta.refrescar()
        self.lbl_estado.configure(text="● Desconectado", text_color=tema.TENUE)
        if hasattr(self, "yo"):
            self._actualizar_controles()
        if conectado and avisar:
            self._log("Desconectado. Los mensajes pendientes siguen en la carpeta.")

    def _nueva_sesion(self):
        self.entrada_sesion.delete(0, "end")
        self.entrada_sesion.insert(0, uuid4().hex[:8])

    def _actualizar_controles(self):
        conectado = self.canal is not None
        config = "disabled" if conectado or self._generando else "normal"
        for control in (self.sel_rol, self.sel_tr, self.entrada_carpeta, self.btn_carpeta,
                        self.entrada_sesion, self.btn_sesion):
            control.configure(state=config)
        self.btn_conectar.configure(state=config)
        self.btn_desconectar.configure(state="normal" if conectado else "disabled")
        self.btn_recibir.configure(state="normal" if conectado else "disabled")
        parametros = self.yo.nombre == "Alice" and self.yo.p is None and not self._generando
        for control in (self.btn_gen_red, self.entrada_p_red, self.entrada_g_red):
            control.configure(state="normal" if parametros else "disabled")
        self.btn_pub_red.configure(state="normal" if parametros and conectado else "disabled")

    def _mostrar_error(self, texto):
        self.lbl_estado.configure(text=f"⚠ {texto}", text_color=tema.EVE)
        if texto != self._ultimo_error:
            self._log(f"⚠ {texto}")
        self._ultimo_error = texto

    def destroy(self):
        if self._sondeo is not None:
            self.after_cancel(self._sondeo)
            self._sondeo = None
        self.canal = None
        super().destroy()

    def _enviar(self, quien):
        if self.canal is None:
            raise ErrorProtocolo("Primero conectá la carpeta compartida.")
        clave = "A" if quien.nombre == "Alice" else "B"
        m = Mensaje(quien.nombre, "Bob" if clave == "A" else "Alice", "PUBLICA", {clave: quien.publica})
        self.canal.enviar(m)
        self._publicos_eve.update(m.datos)
        self._log(f"Enviado:\n{m.a_texto()}")

    def datos_para_eve(self):
        """Instantánea de datos públicos, sin leer ni consumir la cola."""
        return {k: self._publicos_eve[k] for k in ("p", "g", "A") if k in self._publicos_eve}

    def _log(self, texto):
        self.registro.configure(state="normal")
        self.registro.insert("end", texto + "\n")
        self.registro.configure(state="disabled")
