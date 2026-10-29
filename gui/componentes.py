"""Piezas reutilizables de la interfaz."""
import customtkinter as ctk

from core.aritmetica import Paso
from gui import tema
from protocolo.sesion import ErrorProtocolo, Estado, Participante
from transporte.canal import ErrorCanal


class Tarjeta(ctk.CTkFrame):
    """Panel con borde redondeado y título."""

    def __init__(self, master, titulo: str = "", subtitulo: str = "", color=None,
                 color_titulo=None, **kw):
        super().__init__(master, fg_color=tema.PANEL, corner_radius=14,
                         border_width=1, border_color=color or tema.BORDE, **kw)
        self.grid_columnconfigure(0, weight=1)
        fila = 0
        if titulo:
            ctk.CTkLabel(self, text=titulo, font=tema.fuente(15, "bold"),
                         text_color=color_titulo or color or tema.TEXTO, anchor="w").grid(
                row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
            fila = 1
        if subtitulo:
            ctk.CTkLabel(self, text=subtitulo, font=tema.fuente(11), text_color=tema.TENUE,
                         anchor="w", justify="left").grid(
                row=fila, column=0, sticky="ew", padx=16, pady=(0, 4))
            fila += 1
        self.siguiente_fila = fila


class CampoValor(ctk.CTkFrame):
    """Etiqueta + número grande en monoespaciada + botón copiar."""

    def __init__(self, master, titulo: str, color=tema.TEXTO, destacado=False,
                 compacto=False, en_linea=False, largo_compacto=12):
        super().__init__(master, fg_color=tema.PANEL_2, corner_radius=10,
                         border_width=1 if destacado else 0, border_color=color)
        self.grid_columnconfigure(1 if en_linea else 0, weight=1)
        self._valor: int | None = None
        self._compacto = compacto
        self._largo_compacto = largo_compacto
        etiqueta = ctk.CTkLabel(self, text=titulo, font=tema.fuente(10), text_color=tema.TENUE,
                                 height=16 if compacto else 28, width=72 if en_linea else 0, anchor="w")
        etiqueta.grid(row=0, column=0, sticky="w" if en_linea else "ew", padx=10,
                      pady=4 if en_linea else (3, 0))
        self._lbl = ctk.CTkLabel(self, text="—", font=tema.fuente_mono(13 if destacado else 12),
                                 text_color=color, anchor="w", height=22 if compacto else 28,
                                 **({"width": 1} if compacto else {}))
        self._lbl.grid(row=0 if en_linea else 1, column=1 if en_linea else 0,
                        sticky="ew", padx=(0, 4) if en_linea else 10,
                        pady=4 if en_linea else (0, 3))
        self._btn = ctk.CTkButton(self, text="Copiar", width=46 if compacto else 56, height=24, font=tema.fuente(11),
                                  fg_color="transparent", border_width=1, border_color=tema.BORDE,
                                  hover_color=tema.BORDE, command=self._copiar)
        self._btn.grid(row=0, column=2 if en_linea else 1,
                        rowspan=1 if en_linea else 2, padx=8)

    def set(self, valor: int | None, oculto=False):
        self._valor = valor
        texto = tema.formatear(valor)
        if self._compacto and valor is not None and len(str(valor)) > self._largo_compacto:
            mitad = (self._largo_compacto - 1) // 2
            texto = f"{str(valor)[:mitad]}…{str(valor)[-mitad:]}"
        self._lbl.configure(text="••••••••" if (oculto and valor is not None) else texto)

    def _copiar(self):
        if self._valor is not None:
            self.clipboard_clear()
            self.clipboard_append(str(self._valor))
            self._btn.configure(text="✓")
            self.after(900, lambda: self._btn.configure(text="Copiar"))


class PanelPasos(Tarjeta):
    """Muestra el paso a paso de la última operación matemática."""

    def __init__(self, master, alto=200, compacto=False):
        super().__init__(master, "Paso a paso",
                         "" if compacto else "Detalle de la última operación (lo provee core/aritmetica.py)")
        self.caja = ctk.CTkTextbox(self, font=tema.fuente_mono(12), fg_color=tema.PANEL_2,
                                   text_color=tema.TEXTO, corner_radius=10, wrap="none", height=alto)
        self.caja.grid(row=self.siguiente_fila, column=0, sticky="nsew", padx=12, pady=(4, 12))
        self.grid_rowconfigure(self.siguiente_fila, weight=1)
        self.mostrar("Todavía no se hizo ninguna operación.", [])

    def mostrar(self, titulo: str, pasos: list[Paso]):
        self.caja.configure(state="normal")
        self.caja.delete("1.0", "end")
        self.caja.insert("end", f"▸ {titulo}\n\n")
        for i, paso in enumerate(pasos, 1):
            linea = f"  {i:>2}. {paso.descripcion}"
            if paso.valor is not None:
                linea += f"\n      = {tema.formatear(paso.valor, 60)}"
            self.caja.insert("end", linea + "\n")
        self.caja.configure(state="disabled")


class ChipEstado(ctk.CTkLabel):
    COLORES = {
        Estado.SIN_PARAMETROS: tema.TENUE,
        Estado.CON_PARAMETROS: tema.AVISO,
        Estado.PUBLICA_LISTA: tema.ALICE,
        Estado.SECRETO_LISTO: tema.OK,
    }

    def __init__(self, master):
        super().__init__(master, text="", font=tema.fuente(11, "bold"), corner_radius=10,
                         fg_color=tema.PANEL_2, padx=10, pady=2)

    def set(self, estado: Estado):
        self.configure(text=f"● {estado.value}", text_color=self.COLORES[estado])


class TarjetaParticipante(Tarjeta):
    """Panel completo de Alice o de Bob: privada → pública → enviar → secreto.

    callbacks:
     al_enviar(participante)            -> la vista decide por qué canal mandar
     al_mostrar_pasos(titulo, pasos)    -> la vista lo manda al PanelPasos
    """

    def __init__(self, master, participante: Participante, color: str, otro: str,
                 priv: str, pub: str, pub_otro: str, al_enviar, al_mostrar_pasos,
                 compacto=False, al_actualizar=None, solo_lectura=False):
        super().__init__(master, color=color)
        self.p = participante
        self.color, self.otro = color, otro
        self.priv, self.pub, self.pub_otro = priv, pub, pub_otro
        self.al_enviar, self.al_mostrar_pasos = al_enviar, al_mostrar_pasos
        self.al_actualizar = al_actualizar
        self._ocultar = True
        self._bloqueada = False
        self._controles_privada = []
        self.solo_lectura = solo_lectura
        
        # 1. Contenedor scrolleable interno para evitar que se corte el contenido al cambiar el tamaño
        contenedor = ctk.CTkFrame if compacto else ctk.CTkScrollableFrame
        self.scroll_interno = contenedor(self, fg_color="transparent", corner_radius=0)
        self.scroll_interno.grid(row=self.siguiente_fila, column=0, sticky="nsew", padx=2, pady=2)
        self.grid_rowconfigure(self.siguiente_fila, weight=1)
        self.scroll_interno.grid_columnconfigure(0, weight=1)

        if solo_lectura:
            self._construir_remota()
        elif compacto:
            self._construir_compacta()
        else:
            self._construir()
        self.refrescar()

    def _construir_remota(self):
        t = self.scroll_interno
        cab = ctk.CTkFrame(t, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        cab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cab, text=self.p.nombre, font=tema.fuente(15, "bold"),
                     text_color=self.color).grid(row=0, column=0, sticky="w")
        self.chip = ChipEstado(cab)
        self.chip.grid(row=0, column=1)
        ctk.CTkLabel(t, text="Controlado desde la otra PC", text_color=tema.TENUE,
                     font=tema.fuente(12)).grid(row=1, column=0, sticky="w", padx=12, pady=(5, 0))
        ctk.CTkLabel(t, text=f"La privada {self.priv} permanece en ese equipo.",
                     text_color=tema.TENUE, font=tema.fuente(11)).grid(
            row=2, column=0, sticky="w", padx=12, pady=(0, 10))
        for fila, (atributo, titulo, color) in enumerate([
            ("campo_pub", f"Pública {self.pub}", self.color),
            ("campo_recibido", "Tu pública", tema.TEXTO),
            ("campo_secreto", "Su secreto K", tema.TENUE),
        ], 3):
            campo = CampoValor(t, titulo, color, compacto=True, en_linea=True)
            campo.grid(row=fila, column=0, sticky="ew", padx=12, pady=(0, 5))
            setattr(self, atributo, campo)
        self.lbl_error = ctk.CTkLabel(t, text="", height=18, font=tema.fuente(11))
        self.lbl_error.grid(row=6, column=0)

    def _construir_compacta(self):
        """Controles del modo local; la escena muestra a los participantes."""
        t = self.scroll_interno
        cab = ctk.CTkFrame(t, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        cab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cab, text=self.p.nombre, font=tema.fuente(15, "bold"),
                     text_color=self.color).grid(row=0, column=0, sticky="w")
        self.chip = ChipEstado(cab)
        self.chip.grid(row=0, column=1)

        fila = ctk.CTkFrame(t, fg_color="transparent")
        fila.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        fila.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(fila, text=f"Privada {self.priv}", font=tema.fuente(12)).grid(
            row=0, column=0, sticky="w")
        fila.grid_columnconfigure(0, weight=1)
        fila.grid_columnconfigure(1, weight=0)
        self.entrada_priv = ctk.CTkEntry(fila, placeholder_text="2 a p-2", show="•",
                                         height=28, width=100, font=tema.fuente_mono(12))
        self.entrada_priv.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(3, 0))
        self.entrada_priv.bind("<Return>", lambda _e: self._usar_privada())
        ver = ctk.CTkButton(fila, text="Ver", width=58, height=28,
                            fg_color=tema.PANEL_2, command=self._alternar_ver)
        self.btn_ver = ver
        ver.grid(row=0, column=1, padx=(5, 0))
        aleatoria = ctk.CTkButton(fila, text="Aleatoria", width=70, height=28,
                                  fg_color=tema.PANEL_2, command=self._aleatoria)
        aleatoria.grid(row=0, column=2, padx=(5, 0))
        self._controles_privada = [self.entrada_priv, ver, aleatoria]

        acciones = ctk.CTkFrame(t, fg_color="transparent")
        acciones.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 7))
        acciones.grid_columnconfigure((0, 1, 2), weight=1, uniform="acciones")
        for i, (atributo, texto, fn) in enumerate([
            ("btn_publica", f"Calcular {self.pub}", self._calcular_publica),
            ("btn_enviar", f"Enviar {self.pub} {'→' if self.pub == 'A' else '←'}", self._enviar),
            ("btn_secreto", "Derivar K", self._derivar),
        ]):
            boton = ctk.CTkButton(acciones, text=texto, width=80, height=28,
                                   font=tema.fuente(12, "bold"), fg_color=self.color,
                                   text_color="#0b0f18", command=fn)
            boton.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 5, 0))
            setattr(self, atributo, boton)

        valores = ctk.CTkFrame(t, fg_color="transparent")
        valores.grid(row=3, column=0, sticky="ew", padx=12)
        valores.grid_columnconfigure(0, weight=1)
        for i, (atributo, titulo, color) in enumerate([
            ("campo_pub", f"Pública {self.pub}", self.color),
            ("campo_recibido", f"Recibido {self.pub_otro}", tema.TEXTO),
            ("campo_secreto", "Secreto K", tema.OK),
        ]):
            campo = CampoValor(valores, titulo, color, compacto=True, en_linea=True)
            campo.grid(row=i, column=0, sticky="ew", pady=(0 if i == 0 else 4, 0))
            setattr(self, atributo, campo)
        self.lbl_error = ctk.CTkLabel(t, text="", height=18, text_color=tema.EVE,
                                      font=tema.fuente(11), anchor="w", wraplength=240, width=1)
        self.lbl_error.grid(row=4, column=0, sticky="ew", padx=12, pady=(2, 4))
        t.bind("<Configure>", lambda e: self.lbl_error.configure(
            wraplength=max(160, e.width / self._get_widget_scaling() - 24)), add="+")

    def bloquear(self, si):
        self._bloqueada = si
        self.refrescar()

    # -- construcción ------------------------------------------------------------
    def _construir(self):
        # Nota: Ahora los elementos internos se empaquetan dentro de self.scroll_interno en lugar de self
        cab = ctk.CTkFrame(self.scroll_interno, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        cab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(cab, text=self.p.nombre[0], width=34, height=34, corner_radius=17,
                     fg_color=self.color, text_color="#0b0f18",
                     font=tema.fuente(16, "bold")).grid(row=0, column=0, rowspan=2)
        ctk.CTkLabel(cab, text=self.p.nombre, font=tema.fuente(18, "bold"),
                     anchor="w").grid(row=0, column=1, sticky="w", padx=10)
        self.chip = ChipEstado(cab)
        self.chip.grid(row=1, column=1, sticky="w", padx=8)

        # 1. privada
        self._titulo_paso(1, f"1 · Clave privada {self.priv}  (nunca sale de acá)", 1)
        fila = ctk.CTkFrame(self.scroll_interno, fg_color="transparent")
        fila.grid(row=2, column=0, sticky="ew", padx=14)
        fila.grid_columnconfigure(0, weight=1)
        self.entrada_priv = ctk.CTkEntry(fila, placeholder_text="número entre 2 y p-2",
                                         font=tema.fuente_mono(12), show="•", height=30)
        self.entrada_priv.grid(row=0, column=0, sticky="ew")
        self.entrada_priv.bind("<Return>", lambda _e: self._usar_privada())
        ctk.CTkButton(fila, text="👁", width=32, height=30, fg_color=tema.PANEL_2,
                      hover_color=tema.BORDE, command=self._alternar_ver).grid(row=0, column=1, padx=(6, 0))
        ctk.CTkButton(fila, text="Aleatoria", width=80, height=30, fg_color=tema.PANEL_2,
                      hover_color=tema.BORDE, command=self._aleatoria).grid(row=0, column=2, padx=(6, 0))

        # 2. pública
        self._titulo_paso(3, f"2 · Clave pública  {self.pub} = g^{self.priv} mod p", 3)
        self.btn_publica = self._boton(4, f"Calcular {self.pub}", self._calcular_publica)
        self.campo_pub = CampoValor(self.scroll_interno, f"Clave pública {self.pub}", self.color)
        self.campo_pub.grid(row=5, column=0, sticky="ew", padx=14, pady=(4, 0))

        # 3. enviar / recibir
        self._titulo_paso(6, f"3 · Intercambio por el canal inseguro", 6)
        self.btn_enviar = self._boton(7, f"Enviar {self.pub} a {self.otro}  →", self._enviar)
        self.campo_recibido = CampoValor(self.scroll_interno, f"Recibido de {self.otro}: {self.pub_otro}")
        self.campo_recibido.grid(row=8, column=0, sticky="ew", padx=14, pady=(4, 0))

        # 4. secreto
        self._titulo_paso(9, f"4 · Secreto  K = {self.pub_otro}^{self.priv} mod p", 9)
        self.btn_secreto = self._boton(10, "Derivar secreto compartido", self._derivar)
        self.campo_secreto = CampoValor(self.scroll_interno, "Secreto compartido K", tema.OK, destacado=True)
        self.campo_secreto.grid(row=11, column=0, sticky="ew", padx=14, pady=(4, 0))

        self.lbl_error = ctk.CTkLabel(self.scroll_interno, text="", text_color=tema.EVE, font=tema.fuente(11),
                                      anchor="w", justify="left", wraplength=320)
        self.lbl_error.grid(row=12, column=0, sticky="ew", padx=14, pady=(2, 6))

    def _titulo_paso(self, fila, texto, _):
        ctk.CTkLabel(self.scroll_interno, text=texto, font=tema.fuente(12, "bold"), text_color=tema.TENUE,
                     anchor="w").grid(row=fila, column=0, sticky="ew", padx=14, pady=(8, 3))

    def _boton(self, fila, texto, cmd):
        b = ctk.CTkButton(self.scroll_interno, text=texto, height=30, font=tema.fuente(13, "bold"),
                          fg_color=self.color, hover_color=tema.BORDE, text_color="#0b0f18",
                          command=cmd)
        b.grid(row=fila, column=0, sticky="ew", padx=14)
        return b

    # -- acciones ---------------------------------------------------------------
    def _accion(self, fn):
        """Ejecuta fn mostrando los errores dentro de la tarjeta (no popups)."""
        self.lbl_error.configure(text="")
        try:
            fn()
        except ErrorProtocolo as e:
            self.lbl_error.configure(text=f"⚠ {e}")
        except (ErrorCanal, OSError) as e:
            self.lbl_error.configure(text=f"⚠ No se pudo enviar el mensaje: {e}", text_color=tema.EVE)
        except NotImplementedError as e:
            self.lbl_error.configure(text=f"🛠 Módulo pendiente: {e}", text_color=tema.AVISO)
        except ValueError:
            self.lbl_error.configure(text="⚠ Ingresá un número entero válido.")
        self.refrescar()
        if self.al_actualizar:
            self.al_actualizar()

    def _usar_privada(self):
        def fn():
            texto = self.entrada_priv.get().strip()
            if not texto:
                raise ErrorProtocolo(f"Escribí una clave privada o tocá 'Aleatoria'.")
            self.p.establecer_privada(int(texto))
        self._accion(fn)

    def _aleatoria(self):
        def fn():
            valor = self.p.generar_privada()
            self.entrada_priv.delete(0, "end")
            self.entrada_priv.insert(0, str(valor))
        self._accion(fn)

    def _alternar_ver(self):
        self._ocultar = not self._ocultar
        self.entrada_priv.configure(show="•" if self._ocultar else "")
        if hasattr(self, "btn_ver"):
            self.btn_ver.configure(text="Ver" if self._ocultar else "Ocultar")
        if self.al_actualizar:
            self.al_actualizar()

    def _calcular_publica(self):
        def fn():
            texto = self.entrada_priv.get().strip()
            if texto and (self.p.privada is None or int(texto) != self.p.privada):
                self.p.establecer_privada(int(texto))
            valor, pasos = self.p.calcular_publica()
            self.al_mostrar_pasos(f"{self.p.nombre}: {self.pub} = g^{self.priv} mod p", pasos)
        self._accion(fn)

    def _enviar(self):
        def fn():
            if self.p.publica is None:
                raise ErrorProtocolo(f"Primero calculá {self.pub}.")
            self.al_enviar(self.p)
        self._accion(fn)

    def _derivar(self):
        def fn():
            valor, pasos = self.p.derivar_secreto()
            self.al_mostrar_pasos(f"{self.p.nombre}: K = {self.pub_otro}^{self.priv} mod p", pasos)
        self._accion(fn)

    # -- estado -----------------------------------------------------------------
    def refrescar(self):
        p = self.p
        self.chip.set(p.estado)
        self.campo_pub.set(p.publica)
        self.campo_recibido.set(p.publica_ajena)
        self.campo_secreto.set(p.secreto)
        if self.solo_lectura:
            return
        hay_param = p.p is not None
        self._habilitar(self.btn_publica, hay_param)
        self._habilitar(self.btn_enviar, p.publica is not None)
        self._habilitar(self.btn_secreto, p.publica_ajena is not None)
        if self._bloqueada:
            for boton in (self.btn_publica, self.btn_enviar, self.btn_secreto):
                self._habilitar(boton, False)
        for control in self._controles_privada:
            control.configure(state="disabled" if self._bloqueada else "normal")
        if p.privada is None and hay_param is False:
            self.entrada_priv.delete(0, "end")

    def _habilitar(self, boton, si: bool):
        boton.configure(state="normal" if si else "disabled",
                        fg_color=self.color if si else tema.PANEL_2,
                        text_color="#0b0f18" if si else tema.TENUE)
