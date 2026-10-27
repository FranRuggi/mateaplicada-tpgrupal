"""Modo local: Alice | canal inseguro (Eve) | Bob en la misma ventana."""
import customtkinter as ctk

from core import aritmetica
from gui import tema
from gui.componentes import CampoValor, PanelPasos, Tarjeta, TarjetaParticipante
from protocolo.sesion import ErrorProtocolo, Participante
from transporte.canal import CanalMemoria, Mensaje


class VistaModoLocal(ctk.CTkFrame):
    def __init__(self, master, ir_a_eve):
        super().__init__(master, fg_color="transparent")
        self.ir_a_eve = ir_a_eve
        self.alice, self.bob = Participante("Alice"), Participante("Bob")
        self.canal = CanalMemoria()
        self.canal.observar(self._al_pasar_mensaje)
        self.eve_sabe: dict[str, int] = {}

        self.grid_columnconfigure((0, 2), weight=5, uniform="col")
        self.grid_columnconfigure(1, weight=4, uniform="col")
        self.grid_rowconfigure(1, weight=1)

        self._barra_parametros().grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.t_alice = TarjetaParticipante(self, self.alice, tema.ALICE, "Bob", "a", "A", "B",
                                           self._enviar, self._mostrar_pasos)
        self.t_alice.grid(row=1, column=0, sticky="nsew")
        self._panel_canal().grid(row=1, column=1, sticky="nsew", padx=10)
        self.t_bob = TarjetaParticipante(self, self.bob, tema.BOB, "Alice", "b", "B", "A",
                                         self._enviar, self._mostrar_pasos)
        self.t_bob.grid(row=1, column=2, sticky="nsew")

        abajo = ctk.CTkFrame(self, fg_color="transparent")
        abajo.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(10, 0))
        abajo.grid_columnconfigure(0, weight=1)
        self.banner = ctk.CTkLabel(abajo, text="", height=0, corner_radius=10,
                                   font=tema.fuente(14, "bold"))
        self.banner.grid(row=0, column=0, sticky="ew")
        self.pasos = PanelPasos(abajo, alto=78, compacto=True)
        self.pasos.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

    # -- barra de parámetros públicos ---------------------------------------------
    def _barra_parametros(self):
        t = Tarjeta(self)
        t.grid_columnconfigure(4, weight=1)
        ctk.CTkLabel(t, text="Parámetros públicos", font=tema.fuente(15, "bold")).grid(
            row=0, column=0, padx=(16, 12), pady=(10, 2))
        self.sel_bits = ctk.CTkSegmentedButton(t, values=["16", "32", "64", "128", "256"],
                                               font=tema.fuente(12))
        self.sel_bits.set("64")
        self.sel_bits.grid(row=0, column=1)
        ctk.CTkLabel(t, text="bits", text_color=tema.TENUE).grid(row=0, column=2, padx=(6, 10))
        self.btn_generar = ctk.CTkButton(t, text="Generar p y g", width=120,
                                         command=self._generar_parametros)
        self.btn_generar.grid(row=0, column=3, padx=(0, 12))

        campos = ctk.CTkFrame(t, fg_color="transparent")
        campos.grid(row=0, column=4, sticky="ew")
        campos.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(campos, text="p =", font=tema.fuente_mono(13)).grid(row=0, column=0, padx=(0, 4))
        self.entrada_p = ctk.CTkEntry(campos, font=tema.fuente_mono(12), height=32,
                                      placeholder_text="primo (o generalo)")
        self.entrada_p.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(campos, text="g =", font=tema.fuente_mono(13)).grid(row=0, column=2, padx=(10, 4))
        self.entrada_g = ctk.CTkEntry(campos, font=tema.fuente_mono(12), width=70, height=32)
        self.entrada_g.grid(row=0, column=3)

        ctk.CTkButton(t, text="Alice los publica →", width=150, fg_color=tema.ALICE,
                      text_color="#0b0f18", font=tema.fuente(13, "bold"),
                      command=self._publicar_parametros).grid(row=0, column=5, padx=12)
        ctk.CTkButton(t, text="Reiniciar", width=80, fg_color="transparent", border_width=1,
                      border_color=tema.BORDE, hover_color=tema.BORDE,
                      command=self.reiniciar).grid(row=0, column=6, padx=(0, 12))
        self.lbl_param = ctk.CTkLabel(t, text="", font=tema.fuente(11), text_color=tema.TENUE,
                                      anchor="w")
        self.lbl_param.grid(row=1, column=0, columnspan=7, sticky="ew", padx=16, pady=(0, 4))
        return t

    def _generar_parametros(self):
        bits = int(self.sel_bits.get())
        self.btn_generar.configure(state="disabled", text="Generando…")
        self.lbl_param.configure(text=f"Buscando un primo seguro de {bits} bits…", text_color=tema.TENUE)
        self.update_idletasks()
        def listo(res):
            p, g, pasos = res
            self.entrada_p.delete(0, "end"); self.entrada_p.insert(0, str(p))
            self.entrada_g.delete(0, "end"); self.entrada_g.insert(0, str(g))
            self.btn_generar.configure(state="normal", text="Generar p y g")
            self.lbl_param.configure(text="Listo. Ahora Alice tiene que publicarlos por el canal.",
                                     text_color=tema.OK)
            self._mostrar_pasos(f"Generación de p ({bits} bits) y g", pasos)

        def fallo(e):
            self.btn_generar.configure(state="normal", text="Generar p y g")
            self.lbl_param.configure(text=f"⚠ {e}", text_color=tema.EVE)

        tema.correr_en_hilo(self, lambda: aritmetica.generar_parametros(bits), listo, fallo)

    def _publicar_parametros(self):
        try:
            p, g = int(self.entrada_p.get()), int(self.entrada_g.get())
            self.reiniciar(limpiar_campos=False)
            self.alice.establecer_parametros(p, g)
            self.canal.enviar(Mensaje("Alice", "Bob", "PARAMETROS", {"p": p, "g": g}))
            m = self.canal.recibir("Bob")
            self.bob.establecer_parametros(m.datos["p"], m.datos["g"])
            self.lbl_param.configure(text="✔ p y g acordados (y Eve también los conoce).",
                                     text_color=tema.OK)
        except ValueError:
            self.lbl_param.configure(text="⚠ p y g tienen que ser números enteros.", text_color=tema.EVE)
        except ErrorProtocolo as e:
            self.lbl_param.configure(text=f"⚠ {e}", text_color=tema.EVE)
        self._refrescar()

    # -- canal ------------------------------------------------------------------
    def _panel_canal(self):
        t = Tarjeta(self, "Canal inseguro", "Todo lo que viaja por acá lo ve Eve", color_titulo=tema.TEXTO)
        t.grid_rowconfigure(t.siguiente_fila, weight=1)
        self.lista_msgs = ctk.CTkScrollableFrame(t, fg_color=tema.PANEL_2, corner_radius=10)
        self.lista_msgs.grid(row=t.siguiente_fila, column=0, sticky="nsew", padx=12, pady=(4, 8))
        self.lista_msgs.grid_columnconfigure(0, weight=1)

        eve = ctk.CTkFrame(t, fg_color=tema.PANEL_2, corner_radius=10, border_width=1,
                           border_color=tema.EVE)
        eve.grid(row=t.siguiente_fila + 1, column=0, sticky="ew", padx=12, pady=(0, 12))
        eve.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(eve, text="👁  Lo que sabe Eve", font=tema.fuente(13, "bold"),
                     text_color=tema.EVE).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 2))
        self.eve_lbls = {}
        for i, k in enumerate(["p", "g", "A", "B"], 1):
            ctk.CTkLabel(eve, text=f"{k} =", font=tema.fuente_mono(12), text_color=tema.TENUE).grid(
                row=i, column=0, sticky="w", padx=(10, 4))
            lbl = ctk.CTkLabel(eve, text="—", font=tema.fuente_mono(12), anchor="w")
            lbl.grid(row=i, column=1, sticky="ew")
            self.eve_lbls[k] = lbl
        ctk.CTkLabel(eve, text="K = ???   (le falta a o b)",
                     font=tema.fuente_mono(11), text_color=tema.EVE, anchor="w").grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 2))
        ctk.CTkButton(eve, text="Intentar el ataque de Eve →", height=28, fg_color="transparent",
                      border_width=1, border_color=tema.EVE, text_color=tema.EVE,
                      hover_color=tema.BORDE,
                      command=lambda: self.ir_a_eve(self.eve_sabe)).grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 10))
        return t

    def _al_pasar_mensaje(self, m: Mensaje):
        """Observador del canal: dibuja la burbuja y actualiza lo que sabe Eve."""
        color = tema.ALICE if m.remitente == "Alice" else tema.BOB
        flecha = "→" if m.remitente == "Alice" else "←"
        burbuja = ctk.CTkFrame(self.lista_msgs, fg_color=tema.PANEL, corner_radius=8,
                               border_width=1, border_color=color)
        burbuja.grid(sticky="ew", pady=4, padx=2)
        burbuja.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(burbuja, text=f"{m.remitente} {flecha} {m.destinatario}  ·  {m.tipo}",
                     font=tema.fuente(11, "bold"), text_color=color, anchor="w").grid(
            sticky="ew", padx=8, pady=(4, 0))
        for k, v in m.datos.items():
            ctk.CTkLabel(burbuja, text=f"{k} = {tema.formatear(v, 20)}", font=tema.fuente_mono(11),
                         anchor="w").grid(sticky="ew", padx=8)
        ctk.CTkFrame(burbuja, height=4, fg_color="transparent").grid()
        self.eve_sabe.update(m.datos)
        for k, lbl in self.eve_lbls.items():
            lbl.configure(text=tema.formatear(self.eve_sabe.get(k), 20))

    def _enviar(self, quien: Participante):
        otro = self.bob if quien is self.alice else self.alice
        clave = "A" if quien is self.alice else "B"
        self.canal.enviar(Mensaje(quien.nombre, otro.nombre, "PUBLICA", {clave: quien.publica}))
        m = self.canal.recibir(otro.nombre)
        otro.recibir_publica(m.datos[clave])
        self._refrescar()

    # -- comunes ------------------------------------------------------------------
    def _mostrar_pasos(self, titulo, pasos):
        self.pasos.mostrar(titulo, pasos)
        self._refrescar()

    def _refrescar(self):
        self.t_alice.refrescar()
        self.t_bob.refrescar()
        ka, kb = self.alice.secreto, self.bob.secreto
        if ka is not None and kb is not None:
            if ka == kb:
                self.banner.configure(
                    text="✔  Alice y Bob llegaron a la MISMA clave K sin haberla enviado nunca",
                    fg_color="#16392a", text_color=tema.OK, height=32)
            else:
                self.banner.configure(text="✘  Las claves no coinciden: revisar el motor matemático",
                                      fg_color="#3a1c22", text_color=tema.EVE, height=32)
        else:
            self.banner.configure(text="", fg_color="transparent", height=0)

    def reiniciar(self, limpiar_campos=True):
        self.alice.reiniciar(); self.bob.reiniciar()
        self.eve_sabe.clear()
        for w in self.lista_msgs.winfo_children():
            w.destroy()
        for lbl in self.eve_lbls.values():
            lbl.configure(text="—")
        for t in (self.t_alice, self.t_bob):
            t.entrada_priv.delete(0, "end")
            t.lbl_error.configure(text="")
        if limpiar_campos:
            self.entrada_p.delete(0, "end"); self.entrada_g.delete(0, "end")
            self.lbl_param.configure(text="")
            self.pasos.mostrar("Todavía no se hizo ninguna operación.", [])
        self._refrescar()
