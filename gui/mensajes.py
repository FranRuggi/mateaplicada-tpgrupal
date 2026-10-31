"""Panel reutilizable: redactar, ver la recepción y seguir la lectura de Eve."""
import base64
import customtkinter as ctk

from core.cifrado import ErrorCifrado
from gui import tema
from protocolo.sesion import ErrorProtocolo
from transporte.canal import ErrorCanal


def registrar_lecturas(nuevas, log):
    """Relatar solo operaciones reales, sin copiar el texto al registro del canal."""
    for registro, lector, resultado in nuevas:
        origen = registro.mensaje.remitente
        if isinstance(resultado, ErrorCifrado):
            log(f"{lector} no pudo descifrar el mensaje de {origen}: falló la autenticación.")
        elif lector == "Eve":
            log(f"Eve descifró el mensaje de {origen} con la K reconstruida por su ataque.")
        else:
            log(f"{lector} descifró el mensaje de {origen} con su K y verificó su autenticidad.")


def intercepcion_para_escena(modelo):
    """La escena recibe el cifrado y únicamente el texto que Eve sí recuperó."""
    if not modelo.registros:
        return None
    registro = modelo.registros[-1]
    lectura = registro.lecturas.get("Eve")
    return {"id": registro.mensaje.datos["id"],
            "cifrado": base64.b64encode(registro.sobre.texto_cifrado).decode(),
            "texto": lectura if isinstance(lectura, str) else None}


class PanelMensajes(ctk.CTkFrame):
    def __init__(self, master, al_enviar, atacar, detener, al_descifrar, roles=("Alice", "Bob")):
        super().__init__(master, fg_color="transparent")
        self.al_enviar = al_enviar
        self.al_descifrar = al_descifrar
        self.roles = roles
        self._firma = None
        self._ultimo_sobre = ""
        self._modelo = self._ataque = None
        self._siguiente_id = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew")
        barra.grid_columnconfigure(0, weight=1)
        self.sel_rol = ctk.CTkSegmentedButton(barra, values=list(roles), command=self._cambiar_rol)
        self.sel_rol.set(roles[0])
        self.sel_rol.grid(row=0, column=0, sticky="w")
        self.btn_enviar = ctk.CTkButton(barra, text="Cifrar y enviar →", width=150, height=28,
                                       command=self.enviar)
        self.btn_enviar.grid(row=0, column=1, padx=(8, 0))
        self.entrada = ctk.CTkTextbox(self, height=48, font=tema.fuente(12), fg_color=tema.PANEL_2)
        self.entrada.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.estado = ctk.CTkLabel(self, text="", font=tema.fuente(11), anchor="w", height=19,
                                   text_color=tema.TENUE, wraplength=650, justify="left")
        self.estado.grid(row=2, column=0, sticky="ew")
        self.bind("<Configure>", lambda e: self.estado.configure(wraplength=max(180, e.width-12)))
        self.tabs = ctk.CTkTabview(self, height=115, fg_color=tema.PANEL_2)
        self.tabs.grid(row=3, column=0, sticky="nsew")
        conversacion = self.tabs.add("Conversación")
        eve = self.tabs.add("Eve / canal")
        for tab in (conversacion, eve):
            tab.grid_columnconfigure(0, weight=1)
        conversacion.grid_rowconfigure(1, weight=1)
        eve.grid_rowconfigure(1, weight=1)
        recepcion = ctk.CTkFrame(conversacion, fg_color="transparent")
        recepcion.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        recepcion.grid_columnconfigure(0, weight=1)
        self.lbl_pendientes = ctk.CTkLabel(recepcion, text="Sin pendientes", width=1, anchor="w",
                                          font=tema.fuente(11), text_color=tema.TENUE)
        self.lbl_pendientes.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.btn_descifrar = ctk.CTkButton(recepcion, text="Descifrar mensaje", width=125, height=26,
                                          font=tema.fuente(11), command=self.descifrar, state="disabled")
        self.btn_descifrar.grid(row=0, column=1)
        self.conversacion = self._texto(conversacion, 1)
        acciones = ctk.CTkFrame(eve, fg_color="transparent")
        acciones.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.btn_ataque = ctk.CTkButton(acciones, text="Intentar ataque", width=105, height=25,
                                       font=tema.fuente(11),
                                       fg_color=tema.EVE, text_color="#0b0f18", command=atacar)
        self.btn_ataque.pack(side="left")
        self.btn_detener = ctk.CTkButton(acciones, text="Detener", width=55, height=25,
                                        font=tema.fuente(11), command=detener)
        self.btn_detener.pack(side="left", padx=4)
        self.btn_copiar = ctk.CTkButton(acciones, text="Copiar sobre", width=85, height=25,
                                       font=tema.fuente(11),
                                       command=self._copiar)
        self.btn_copiar.pack(side="left")
        self.eve = self._texto(eve, 1)
        self._motivos = {rol: "Primero completá el intercambio y derivá K." for rol in roles}
        self._estado()

    def _texto(self, master, fila):
        caja = ctk.CTkTextbox(master, height=55, font=tema.fuente(12), wrap="word")
        caja.grid(row=fila, column=0, sticky="nsew")
        caja.configure(state="disabled")
        return caja

    def _estado(self):
        motivo = self._motivos[self.sel_rol.get()]
        self.btn_enviar.configure(state="disabled" if motivo else "normal")
        self.estado.configure(text=motivo or "AES-256-GCM · Por el canal viajan el sobre cifrado y sus datos públicos.",
                               text_color=tema.TENUE)

    def _cambiar_rol(self, rol):
        self.sel_rol.set(rol)
        self._estado()
        if self._modelo is not None:
            self.actualizar(self._modelo, self._motivos, self._ataque)

    def descifrar(self):
        try:
            rol = self.sel_rol.get()
            if self._motivos[rol]:
                raise ValueError(self._motivos[rol])
            if self._siguiente_id is None:
                raise ValueError("No hay mensajes recibidos pendientes de descifrar.")
            self.al_descifrar(rol, self._siguiente_id)
        except (ValueError, OSError, RuntimeError, ErrorCanal, ErrorProtocolo) as error:
            self.estado.configure(text=str(error), text_color=tema.EVE)

    def enviar(self):
        try:
            if self._motivos[self.sel_rol.get()]:
                raise ValueError(self._motivos[self.sel_rol.get()])
            texto = self.entrada.get("1.0", "end-1c")
            if not texto:
                raise ValueError("Escribí un mensaje para enviar.")
            self.al_enviar(self.sel_rol.get(), texto)
            self.entrada.delete("1.0", "end")
        except (ValueError, OSError, RuntimeError, ErrorCanal, ErrorProtocolo) as error:
            self.estado.configure(text=str(error), text_color=tema.EVE)

    def actualizar(self, modelo, motivos, ataque):
        self._modelo, self._ataque = modelo, ataque
        if motivos != self._motivos:
            self._motivos = motivos
            self._estado()
        self.btn_ataque.configure(state=ataque.btn.cget("state"))
        self.btn_detener.configure(state=ataque.btn_cancelar.cget("state"))
        self.btn_copiar.configure(state="normal" if modelo.registros else "disabled")
        rol = self.sel_rol.get()
        pendientes = modelo.pendientes(rol)
        self._siguiente_id = pendientes[0].mensaje.datos["id"] if pendientes else None
        cantidad = len(pendientes)
        self.lbl_pendientes.configure(text=f"{rol} · {cantidad} {'pendiente' if cantidad == 1 else 'pendientes'}")
        self.btn_descifrar.configure(state="normal" if pendientes and not motivos[rol] else "disabled")
        conversacion, eve = [], []
        for i, r in enumerate(modelo.registros, 1):
            m = r.mensaje
            titulo = f"{i}. {m.remitente} → {m.destinatario}"
            lectura = r.lecturas.get(m.destinatario)
            self._ultimo_sobre = r.mensaje.datos["sobre"]
            cifrado = base64.b64encode(r.sobre.texto_cifrado).decode()
            if m.remitente == rol and r.texto_propio is not None:
                conversacion.append(f"{titulo} · Cifrado y enviado\n{r.texto_propio}")
            if m.destinatario == rol:
                muestra = cifrado[:100] + ("…" if len(cifrado) > 100 else "")
                detalle = (f"Pendiente de descifrado. {motivos[rol]}" if motivos[rol] else
                           "Pendiente: pulsá «Descifrar mensaje».") if lectura is None else (
                           str(lectura) if isinstance(lectura, ErrorCifrado) else f"Descifrado por {rol}:\n{lectura}")
                conversacion.append(f"{titulo} · Recibido cifrado\nCifrado (Base64): {muestra}\n{detalle}")
            elif r.texto_propio is None:
                conversacion.append(f"{titulo} · Sobre cifrado observado.")
            visto = r.lecturas.get("Eve")
            detalle = ("Sin K: Eve solo ve el contenido cifrado." if visto is None
                       else str(visto) if isinstance(visto, ErrorCifrado)
                       else f"Eve reconstruyó K y descifró:\n{visto}")
            eve.append(f"{titulo}\nCifrado: {cifrado[:100]}{'…' if len(cifrado) > 100 else ''}\n{detalle}")
        textos = ("\n\n".join(conversacion) or "Los mensajes aparecerán después de enviarlos.",
                  "\n\n".join(eve) or "Eve todavía no interceptó mensajes cifrados.")
        if textos != self._firma:
            self._firma = textos
            for caja, texto in zip((self.conversacion, self.eve), textos):
                caja.configure(state="normal")
                caja.delete("1.0", "end")
                caja.insert("1.0", texto)
                caja.see("end")
                caja.configure(state="disabled")

    def limpiar(self):
        self.entrada.delete("1.0", "end")

    def _copiar(self):
        self.clipboard_clear()
        self.clipboard_append(self._ultimo_sobre)
