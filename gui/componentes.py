"""Piezas reutilizables de la interfaz."""
import customtkinter as ctk

from core.aritmetica import Paso
from gui import tema
from protocolo.sesion import ErrorProtocolo, Estado, Participante


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

    def __init__(self, master, titulo: str, color=tema.TEXTO, destacado=False):
        super().__init__(master, fg_color=tema.PANEL_2, corner_radius=10,
                         border_width=1 if destacado else 0, border_color=color)
        self.grid_columnconfigure(0, weight=1)
        self._valor: int | None = None
        ctk.CTkLabel(self, text=titulo, font=tema.fuente(10), text_color=tema.TENUE,
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=10, pady=(3, 0))
        self._lbl = ctk.CTkLabel(self, text="—", font=tema.fuente_mono(13 if destacado else 12),
                                 text_color=color, anchor="w")
        self._lbl.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 3))
        self._btn = ctk.CTkButton(self, text="Copiar", width=56, height=24, font=tema.fuente(11),
                                  fg_color="transparent", border_width=1, border_color=tema.BORDE,
                                  hover_color=tema.BORDE, command=self._copiar)
        self._btn.grid(row=0, column=1, rowspan=2, padx=8)

    def set(self, valor: int | None, oculto=False):
        self._valor = valor
        self._lbl.configure(text="••••••••" if (oculto and valor is not None) else tema.formatear(valor))

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
                 priv: str, pub: str, pub_otro: str, al_enviar, al_mostrar_pasos):
        super().__init__(master, color=color)
        self.p = participante
        self.color, self.otro = color, otro
        self.priv, self.pub, self.pub_otro = priv, pub, pub_otro
        self.al_enviar, self.al_mostrar_pasos = al_enviar, al_mostrar_pasos
        self._ocultar = True
        self._construir()
        self.refrescar()

    # -- construcción ------------------------------------------------------------
    def _construir(self):
        cab = ctk.CTkFrame(self, fg_color="transparent")
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
        fila = ctk.CTkFrame(self, fg_color="transparent")
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
        self.campo_pub = CampoValor(self, f"Clave pública {self.pub}", self.color)
        self.campo_pub.grid(row=5, column=0, sticky="ew", padx=14, pady=(4, 0))

        # 3. enviar / recibir
        self._titulo_paso(6, f"3 · Intercambio por el canal inseguro", 6)
        self.btn_enviar = self._boton(7, f"Enviar {self.pub} a {self.otro}  →", self._enviar)
        self.campo_recibido = CampoValor(self, f"Recibido de {self.otro}: {self.pub_otro}")
        self.campo_recibido.grid(row=8, column=0, sticky="ew", padx=14, pady=(4, 0))

        # 4. secreto
        self._titulo_paso(9, f"4 · Secreto  K = {self.pub_otro}^{self.priv} mod p", 9)
        self.btn_secreto = self._boton(10, "Derivar secreto compartido", self._derivar)
        self.campo_secreto = CampoValor(self, "Secreto compartido K", tema.OK, destacado=True)
        self.campo_secreto.grid(row=11, column=0, sticky="ew", padx=14, pady=(4, 0))

        self.lbl_error = ctk.CTkLabel(self, text="", text_color=tema.EVE, font=tema.fuente(11),
                                      anchor="w", justify="left", wraplength=320)
        self.lbl_error.grid(row=12, column=0, sticky="ew", padx=14, pady=(2, 6))

    def _titulo_paso(self, fila, texto, _):
        ctk.CTkLabel(self, text=texto, font=tema.fuente(12, "bold"), text_color=tema.TENUE,
                     anchor="w").grid(row=fila, column=0, sticky="ew", padx=14, pady=(8, 3))

    def _boton(self, fila, texto, cmd):
        b = ctk.CTkButton(self, text=texto, height=30, font=tema.fuente(13, "bold"),
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
        except NotImplementedError as e:
            self.lbl_error.configure(text=f"🛠 Módulo pendiente: {e}", text_color=tema.AVISO)
        except ValueError:
            self.lbl_error.configure(text="⚠ Ingresá un número entero válido.")
        self.refrescar()

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
        hay_param = p.p is not None
        self._habilitar(self.btn_publica, hay_param)
        self._habilitar(self.btn_enviar, p.publica is not None)
        self._habilitar(self.btn_secreto, p.publica_ajena is not None)
        if p.privada is None and hay_param is False:
            self.entrada_priv.delete(0, "end")

    def _habilitar(self, boton, si: bool):
        boton.configure(state="normal" if si else "disabled",
                        fg_color=self.color if si else tema.PANEL_2,
                        text_color="#0b0f18" if si else tema.TENUE)
