"""Modo local: escena arcade y controles reales de Alice y Bob."""
import customtkinter as ctk

from core import aritmetica
from gui import tema
from gui.ataque_eve import PanelAtaqueEve
from gui.componentes import Tarjeta, TarjetaParticipante
from gui.escena import EscenaIntercambio
from gui.registro import AreaConRegistro
from protocolo.sesion import ErrorProtocolo, Participante
from transporte.canal import CanalMemoria, Mensaje


class VistaModoLocal(AreaConRegistro):
    def __init__(self, master, ir_a_eve, rol_local=None):
        super().__init__(master)
        self.ir_a_eve = ir_a_eve
        self.alice, self.bob = Participante("Alice"), Participante("Bob")
        self.canal = CanalMemoria()
        self.canal.observar(self._al_pasar_mensaje)
        self.eve_sabe: dict[str, int] = {}
        self._refrescando = False
        self._lista = False
        self._generacion = 0
        self.cuerpo.grid_columnconfigure((0, 2), weight=1)
        self.cuerpo.grid_columnconfigure(1, weight=0)
        self._ancho_central = None
        self._disposicion = None
        self.cuerpo.bind("<Configure>", self._ajustar_ancho, add="+")

        self._barra_parametros().grid(row=0, column=1, sticky="ew", pady=(0, 8))
        self.escena = EscenaIntercambio(self.cuerpo, al_cambiar=self._refrescar)
        self.escena.grid(row=1, column=1, sticky="ew")

        estado = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        estado.grid(row=2, column=1, sticky="ew", pady=(5, 6))
        estado.grid_columnconfigure(0, weight=1)
        self.lbl_escena = ctk.CTkLabel(estado, text="Elegí p y g para comenzar.",
                                       font=tema.fuente(11), text_color=tema.TENUE, anchor="w",
                                       width=1, wraplength=400, justify="left")
        self.lbl_escena.grid(row=0, column=0, sticky="ew")
        self.animar = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(estado, text="Animaciones", variable=self.animar,
                      font=tema.fuente(11), width=110, switch_width=30, switch_height=16,
                      command=lambda: self.escena.establecer_animaciones(self.animar.get())).grid(
            row=0, column=1, padx=10)
        self.controles = ctk.CTkFrame(self.cuerpo, fg_color="transparent")
        self.controles.grid(row=3, column=1, sticky="ew")
        self.controles.grid_columnconfigure((0, 1, 2), weight=1, uniform="participantes")
        self.ataque_eve = PanelAtaqueEve(self.controles, self._ataque_cambio, self._log)
        self.ataque_eve.grid(row=0, column=1, sticky="nsew", padx=6)
        self.btn_eve = self.ataque_eve.btn

        self.t_alice = TarjetaParticipante(
            self.controles, self.alice, tema.ALICE, "Bob", "a", "A", "B",
            self._enviar, self._mostrar_pasos, compacto=True, al_actualizar=self._refrescar,
            solo_lectura=rol_local == "Bob")
        self.t_alice.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.t_bob = TarjetaParticipante(
            self.controles, self.bob, tema.BOB, "Alice", "b", "B", "A",
            self._enviar, self._mostrar_pasos, compacto=True, al_actualizar=self._refrescar,
            solo_lectura=rol_local == "Alice")
        self.t_bob.grid(row=0, column=2, sticky="nsew", padx=(6, 0))

        self.banner = ctk.CTkLabel(self.cuerpo, text="", height=0, corner_radius=8,
                                   font=tema.fuente(13, "bold"), width=1, wraplength=900)
        self.banner.grid(row=4, column=1, sticky="ew", pady=(4, 0))
        self._lista = True
        self._log("Sesión lista. Publicá los parámetros para comenzar.")
        self._refrescar()

    def _ajustar_ancho(self, evento):
        # La columna central crece hasta 1120 unidades; los márgenes absorben
        # el espacio restante de una ventana maximizada.
        ancho = min(evento.width, round(1120 * self._get_widget_scaling()))
        if ancho != self._ancho_central:
            self._ancho_central = ancho
            self.cuerpo.grid_columnconfigure(1, minsize=ancho)
        logico = ancho / self._get_widget_scaling()
        if not self._lista:
            return
        self.lbl_param.configure(wraplength=max(250, logico-24))
        self.lbl_escena.configure(wraplength=max(160, logico-140))
        self.banner.configure(wraplength=max(250, logico-24))
        estrecho = logico < 680
        self._param_generacion.grid(row=1 if estrecho else 0, column=0 if estrecho else 1,
                                    columnspan=3 if estrecho else 1,
                                    sticky="w", padx=(0 if estrecho else 12, 0),
                                    pady=(4, 0) if estrecho else 0)
        campos_estrechos = logico < 560
        self.btn_publicar.grid(row=1 if campos_estrechos else 0,
                                column=0 if campos_estrechos else 4,
                                columnspan=4 if campos_estrechos else 1,
                                sticky="ew", padx=0 if campos_estrechos else (10, 0),
                                pady=(6, 0) if campos_estrechos else 0)
        disposicion = "tres" if logico >= 900 else "dos" if logico >= 640 else "una"
        if disposicion == self._disposicion:
            return
        self._disposicion = disposicion
        for tarjeta in (self.t_alice, self.ataque_eve, self.t_bob):
            tarjeta.grid_forget()
        self.controles.grid_columnconfigure((0, 1, 2), weight=0, minsize=0, uniform="")
        if disposicion == "tres":
            self.controles.grid_columnconfigure((0, 1, 2), weight=1, uniform="participantes")
            for i, tarjeta in enumerate((self.t_alice, self.ataque_eve, self.t_bob)):
                tarjeta.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))
        elif disposicion == "dos":
            self.controles.grid_columnconfigure((0, 1), weight=1, uniform="participantes")
            self.t_alice.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
            self.t_bob.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
            self.ataque_eve.grid(row=1, column=0, columnspan=2, sticky="n", pady=(10, 0))
        else:
            self.controles.grid_columnconfigure(0, weight=1)
            for i, tarjeta in enumerate((self.t_alice, self.ataque_eve, self.t_bob)):
                tarjeta.grid(row=i, column=0, sticky="n", pady=(0 if i == 0 else 10, 0))

    def _barra_parametros(self):
        t = Tarjeta(self.cuerpo)
        t.grid_columnconfigure(1, weight=1)
        arriba = ctk.CTkFrame(t, fg_color="transparent")
        arriba.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(7, 3))
        arriba.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(arriba, text="Parámetros públicos", font=tema.fuente(14, "bold")).grid(
            row=0, column=0, padx=(0, 12))
        self._param_generacion = ctk.CTkFrame(arriba, fg_color="transparent")
        self._param_generacion.grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.sel_bits = ctk.CTkSegmentedButton(self._param_generacion, values=["16", "32", "64", "128", "256"],
                                               font=tema.fuente(11), height=26)
        self.sel_bits.set("64")
        self.sel_bits.grid(row=0, column=0)
        ctk.CTkLabel(self._param_generacion, text="bits", text_color=tema.TENUE,
                     font=tema.fuente(11)).grid(row=0, column=1, padx=(5, 10))
        self.btn_generar = ctk.CTkButton(self._param_generacion, text="Generar p y g", width=110, height=27,
                                         command=self._generar_parametros)
        self.btn_generar.grid(row=0, column=2)
        self.btn_reiniciar = ctk.CTkButton(arriba, text="Reiniciar", width=80, height=27,
                                          fg_color=tema.PANEL_2, command=self.reiniciar)
        self.btn_reiniciar.grid(row=0, column=2)

        campos = ctk.CTkFrame(t, fg_color="transparent")
        campos.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12)
        campos.grid_columnconfigure(1, weight=3)
        campos.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(campos, text="p =", font=tema.fuente_mono(12)).grid(row=0, column=0, padx=(0, 4))
        self.entrada_p = ctk.CTkEntry(campos, font=tema.fuente_mono(12), height=28,
                                      placeholder_text="primo (o generalo)")
        self.entrada_p.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(campos, text="g =", font=tema.fuente_mono(12)).grid(row=0, column=2, padx=(10, 4))
        self.entrada_g = ctk.CTkEntry(campos, font=tema.fuente_mono(12), height=28, width=70)
        self.entrada_g.grid(row=0, column=3, sticky="ew")
        self.btn_publicar = ctk.CTkButton(campos, text="Alice publica p y g →", width=164, height=28,
                                           fg_color=tema.ALICE, text_color="#0b0f18",
                                           font=tema.fuente(12, "bold"), command=self._publicar_parametros)
        self.btn_publicar.grid(row=0, column=4, padx=(10, 0))
        self.lbl_param = ctk.CTkLabel(t, text="", height=19, font=tema.fuente(11),
                                      text_color=tema.TENUE, anchor="w", width=1, justify="left")
        self.lbl_param.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 3))
        return t

    def _generar_parametros(self):
        bits = int(self.sel_bits.get())
        self._generacion += 1
        generacion = self._generacion
        self.btn_generar.configure(state="disabled", text="Generando…")
        self.lbl_param.configure(text=f"Buscando un primo seguro de {bits} bits…", text_color=tema.TENUE)

        def listo(res):
            if generacion != self._generacion:
                return
            p, g, pasos = res
            self.entrada_p.delete(0, "end"); self.entrada_p.insert(0, str(p))
            self.entrada_g.delete(0, "end"); self.entrada_g.insert(0, str(g))
            self.btn_generar.configure(state="normal", text="Generar p y g")
            self.lbl_param.configure(text="Listo. Ahora Alice tiene que publicarlos por el canal.",
                                     text_color=tema.OK)
            self._mostrar_pasos(f"Generación de p ({bits} bits) y g", pasos)

        def fallo(e):
            if generacion != self._generacion:
                return
            self.btn_generar.configure(state="normal", text="Generar p y g")
            self.lbl_param.configure(text=f"⚠ {e}", text_color=tema.EVE)

        tema.correr_en_hilo(self, lambda: aritmetica.generar_parametros(bits), listo, fallo)

    def _publicar_parametros(self):
        try:
            p, g = int(self.entrada_p.get()), int(self.entrada_g.get())
            # Validar antes de vaciar la sesión que se está viendo.
            validacion = Participante("Alice")
            validacion.establecer_parametros(p, g)
            self.reiniciar(limpiar_campos=False)
            self.alice.establecer_parametros(p, g)
            self.canal.enviar(Mensaje("Alice", "Bob", "PARAMETROS", {"p": p, "g": g}))
            m = self.canal.recibir("Bob")
            self.bob.establecer_parametros(m.datos["p"], m.datos["g"])
            self.lbl_param.configure(text="✔ p y g publicados. Las privadas se eligen abajo.",
                                     text_color=tema.OK)
        except ValueError:
            self.lbl_param.configure(text="⚠ p y g tienen que ser números enteros.", text_color=tema.EVE)
        except ErrorProtocolo as e:
            self.lbl_param.configure(text=f"⚠ {e}", text_color=tema.EVE)
        self._refrescar()

    def _al_pasar_mensaje(self, m: Mensaje):
        self.eve_sabe.update(m.datos)
        datos = ", ".join(f"{k} = {v}" for k, v in m.datos.items())
        self._log(f"{m.remitente} → {m.destinatario} · {m.tipo}: {datos}")
        self._log(f"Eve observa una copia de {', '.join(m.datos)}.")
        self.escena.mostrar_mensaje(m)

    def _enviar(self, quien: Participante):
        otro = self.bob if quien is self.alice else self.alice
        clave = "A" if quien is self.alice else "B"
        self.canal.enviar(Mensaje(quien.nombre, otro.nombre, "PUBLICA", {clave: quien.publica}))
        m = self.canal.recibir(otro.nombre)
        otro.recibir_publica(m.datos[clave])
        self._refrescar()

    def datos_para_eve(self):
        """Solo los valores públicos que ya circularon por el canal."""
        return {k: self.eve_sabe[k] for k in ("p", "g", "A") if k in self.eve_sabe}

    def _mostrar_pasos(self, titulo, pasos):
        self.pasos.mostrar(titulo, pasos)
        self._log(titulo)
        if pasos and pasos[-1].valor is not None:
            self._log(f"Resultado: {pasos[-1].valor}")
        self._refrescar()

    def _log(self, texto):
        self.consola.configure(state="normal")
        self.consola.insert("end", f"› {texto}\n")
        self.consola.see("end")
        self.consola.configure(state="disabled")

    def _refrescar(self):
        if not self._lista or self._refrescando:
            return
        self._refrescando = True
        try:
            self.escena.actualizar(self.alice, self.bob,
                                    (self.t_alice._ocultar, self.t_bob._ocultar))
            self.ataque_eve.actualizar_publicos(self.escena.publicos_observados)
            ocupado = self.escena.en_animacion
            self.t_alice.bloquear(ocupado)
            self.t_bob.bloquear(ocupado)
            self.ataque_eve.bloquear_inicio(ocupado)
            if ocupado:
                texto = "Mostrando el intercambio… Los controles vuelven al terminar."
            elif self.alice.p is None:
                texto = "Elegí p y g para comenzar."
            else:
                texto = "Las privadas quedan con cada actor. Eve solo ve lo que pasa por el canal."
            self.lbl_escena.configure(text=texto)
            ka, kb = self.alice.secreto, self.bob.secreto
            if ka is not None and kb is not None:
                coinciden = ka == kb
                self.banner.configure(
                    text="✔ Alice y Bob llegaron a la misma K sin enviarla por el canal" if coinciden
                    else "✘ Las claves no coinciden: revisar el intercambio",
                    fg_color="#16392a" if coinciden else "#3a1c22",
                    text_color=tema.OK if coinciden else tema.EVE, height=28)
            else:
                self.banner.configure(text="", fg_color="transparent", height=0)
        finally:
            self._refrescando = False

    def _ataque_cambio(self, estado):
        self.escena.actualizar_ataque(estado)
        self._refrescar()

    def reiniciar(self, limpiar_campos=True):
        self._generacion += 1
        self.btn_generar.configure(state="normal", text="Generar p y g")
        self.alice.reiniciar(); self.bob.reiniciar()
        self.eve_sabe.clear()
        self.canal = CanalMemoria()
        self.canal.observar(self._al_pasar_mensaje)
        self.ataque_eve.reiniciar()
        self.escena.reiniciar()
        for t in (self.t_alice, self.t_bob):
            # El reinicio también funciona en medio de un envío animado.
            if not t.solo_lectura:
                t.entrada_priv.configure(state="normal")
                t.entrada_priv.delete(0, "end")
            t.lbl_error.configure(text="")
        self.consola.configure(state="normal")
        self.consola.delete("1.0", "end")
        self.consola.configure(state="disabled")
        self.pasos.mostrar("Todavía no se hizo ninguna operación.", [])
        if limpiar_campos:
            self.entrada_p.delete(0, "end"); self.entrada_g.delete(0, "end")
            self.lbl_param.configure(text="")
        self._log("Sesión reiniciada.")
        self._refrescar()
