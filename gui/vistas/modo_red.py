"""Modo red: esta computadora juega UN solo rol y habla con la otra por
archivos .txt (objetivo principal) o por sockets (objetivo secundario)."""
from core import aritmetica
import customtkinter as ctk
from tkinter import filedialog

from gui import tema
from gui.componentes import PanelPasos, Tarjeta, TarjetaParticipante
from protocolo.sesion import Participante
from transporte.canal import CanalArchivo, CanalSocket, Mensaje


class VistaModoRed(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=4, uniform="c")
        self.grid_columnconfigure(1, weight=5, uniform="c")
        self.grid_columnconfigure(2, weight=5, uniform="c")
        self.grid_rowconfigure(0, weight=1)
        self.canal = None

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
    # -- configuración -----------------------------------------------------------
    def _panel_config(self):
        t = Tarjeta(self, "Conexión", "Cada computadora corre la app con un rol distinto")
        f = t.siguiente_fila
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
        ctk.CTkButton(self.op_archivo, text="Elegir…", width=70, fg_color=tema.PANEL_2,
                      hover_color=tema.BORDE, command=self._elegir_carpeta).grid(row=1, column=1, padx=(6, 0))

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
        ctk.CTkButton(t, text="Conectar", height=36, font=tema.fuente(13, "bold"),
                      command=self._conectar).grid(row=f + 6, column=0, sticky="ew", padx=16, pady=(14, 6))
        
        self.lbl_estado = ctk.CTkLabel(t, text="● Desconectado", text_color=tema.TENUE,
                                       font=tema.fuente(12), anchor="w", justify="left", wraplength=250)
        self.lbl_estado.grid(row=f + 7, column=0, sticky="ew", padx=16)

        ctk.CTkLabel(t, text="Alice genera p y g y los manda primero.\nBob espera a recibirlos.",
                     font=tema.fuente(11), text_color=tema.TENUE, justify="left", anchor="w").grid(
            row=f + 8, column=0, sticky="ew", padx=16, pady=(12, 12))
        # --- BOTÓN DE RECEPCIÓN (Para Bob o Alice) ---
        self.btn_recibir = ctk.CTkButton(t, text="📥 Buscar mensajes nuevos", height=28,
                                         fg_color=tema.PANEL_2, text_color=tema.TEXTO,
                                         border_width=1, border_color=tema.BORDE,
                                         command=self._verificar_mensajes)
        self.btn_recibir.grid(row=f + 9, column=0, sticky="ew", padx=16, pady=(8, 12))
        return t
    def _generar_params_red(self):
        # Genera por defecto con 64 bits o los que prefieras
        p, g, pasos = aritmetica.generar_parametros(64)
        self.entrada_p_red.delete(0, "end"); self.entrada_p_red.insert(0, str(p))
        self.entrada_g_red.delete(0, "end"); self.entrada_g_red.insert(0, str(g))
        self.pasos.mostrar("Generación de p y g", pasos)

    def _verificar_mensajes(self):
        if self.canal is None:
            self._log("⚠ Primero debes conectarte a la carpeta o socket.")
            return

        # Intentar recibir un mensaje dirigido al rol actual (self.yo.nombre)
        mensaje = self.canal.recibir(self.yo.nombre)

        if mensaje:
            self._log(f"📥 Recibido de {mensaje.remitente}: tipo '{mensaje.tipo}'")
            # Procesar según el tipo de mensaje recibido
            if mensaje.tipo == "PARAMETROS":
                p = mensaje.datos.get("p")
                g = mensaje.datos.get("g")
                self.yo.establecer_parametros(p, g)
                self._log(f"✔ Parámetros aceptados: p={p}, g={g}")
            elif mensaje.tipo == "PUBLICA":
                clave_ajena = mensaje.datos.get("A") or mensaje.datos.get("B")
                if clave_ajena:
                    self.yo.recibir_publica(clave_ajena)
                    self._log(f"✔ Clave pública ajena recibida: {clave_ajena}")
            # Refrescar la tarjeta visual del participante
            self.tarjeta.refrescar()
        else:
            self._log("ℹ No hay mensajes nuevos en el canal.")
    def _publicar_params_red(self):
        if self.canal is None:
            raise NotImplementedError("Primero conectá el canal.")
        try:
            p = int(self.entrada_p_red.get())
            g = int(self.entrada_g_red.get())
            self.yo.establecer_parametros(p, g)
            # Enviar por el canal de red configurado
            otro = "Bob" if self.yo.nombre == "Alice" else "Alice"
            m = Mensaje(self.yo.nombre, otro, "PARAMETROS", {"p": p, "g": g})
            self.canal.enviar(m)
            self._log(m.a_texto())
        except ValueError:
            self._log("⚠ Error: p y g deben ser números enteros.")
    def _panel_registro(self, master):
        t = Tarjeta(master, "Mensajes en texto plano", "Exactamente lo que se escribe en el .txt / socket")
        self.registro = ctk.CTkTextbox(t, font=tema.fuente_mono(12), fg_color=tema.PANEL_2,
                                       corner_radius=10)
        self.registro.grid(row=t.siguiente_fila, column=0, sticky="nsew", padx=12, pady=(4, 12))
        t.grid_rowconfigure(t.siguiente_fila, weight=1)
        ejemplo = Mensaje("Alice", "Bob", "PUBLICA", {"A": 1234567})
        self._log(f"# Formato de ejemplo (alice_a_bob.txt):\n{ejemplo.a_texto()}")
        return t

    # -- eventos ------------------------------------------------------------------
    def _cambiar_rol(self, rol):
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

    def _cambiar_transporte(self, valor):
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
        try:
            if self.sel_tr.get().startswith("Archivos"):
                self.canal = CanalArchivo(self.entrada_carpeta.get())
                self.canal.recibir(self.yo.nombre)  # prueba
            else:
                self.canal = CanalSocket(self.entrada_host.get(), int(self.entrada_puerto.get()),
                                         es_servidor=self.sel_rol.get() == "Bob")
                self.canal.recibir(self.yo.nombre)
            self.lbl_estado.configure(text="● Conectado", text_color=tema.OK)
        except NotImplementedError as e:
            self.lbl_estado.configure(text=f"🛠 {e}\n(transporte/canal.py)", text_color=tema.AVISO)
        except ValueError:
            self.lbl_estado.configure(text="⚠ El puerto tiene que ser un número.", text_color=tema.EVE)

    def _enviar(self, quien):
        if self.canal is None:
            raise NotImplementedError("Primero conectá el canal (panel izquierdo).")
        clave = "A" if quien.nombre == "Alice" else "B"
        m = Mensaje(quien.nombre, "Bob" if clave == "A" else "Alice", "PUBLICA", {clave: quien.publica})
        self.canal.enviar(m)
        self._log(m.a_texto())

    def _log(self, texto):
        self.registro.configure(state="normal")
        self.registro.insert("end", texto + "\n")
        self.registro.configure(state="disabled")
