"""Ataque de Eve incrustado en una sesión, alimentado solo por datos públicos."""
from dataclasses import dataclass
import threading
import time

import customtkinter as ctk

from core import aritmetica
from gui import tema
from gui.componentes import CampoValor


@dataclass(frozen=True)
class ResultadoBusqueda:
    exponente: int | None
    intentos: int
    segundos: float
    cancelado: bool


class PanelAtaqueEve(ctk.CTkFrame):
    LIMITES = {"10 mil": 10_000, "1 millón": 1_000_000, "10 millones": 10_000_000}

    def __init__(self, master, al_estado, al_registrar):
        super().__init__(master, fg_color="#211c2d", corner_radius=10,
                         border_width=1, border_color="#604359")
        self.al_estado, self.al_registrar = al_estado, al_registrar
        self._datos = {}
        self._resultado = None
        self._secreto = None
        self._b_usada = None
        self._buscando = False
        self._canal_ocupado = False
        self._version = 0
        self._cancelacion = threading.Event()
        self._sondeo_id = None
        self.estado = {"estado": "esperando", "intentos": 0}
        self.grid_columnconfigure(0, weight=1)

        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 7))
        cab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cab, text="Eve", font=tema.fuente(15, "bold"),
                     text_color=tema.EVE).grid(row=0, column=0, sticky="w")
        self.chip = ctk.CTkLabel(cab, text="Datos públicos", font=tema.fuente(11, "bold"),
                                  text_color=tema.EVE, fg_color=tema.PANEL_2,
                                  corner_radius=10, padx=10, height=24)
        self.chip.grid(row=0, column=1)
        datos = ctk.CTkFrame(self, fg_color="transparent")
        datos.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        datos.grid_columnconfigure((0, 1), weight=1, uniform="publicos")
        self.campos = {}
        for i, k in enumerate(("p", "g", "A", "B")):
            campo = CampoValor(datos, k, tema.EVE, compacto=True, largo_compacto=8)
            campo.grid(row=i//2, column=i%2, sticky="ew",
                        padx=(0, 3) if i%2 == 0 else (3, 0),
                        pady=(0 if i < 2 else 5, 0))
            self.campos[k] = campo

        limite = ctk.CTkFrame(self, fg_color="transparent")
        limite.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 7))
        limite.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(limite, text="Máx. intentos", font=tema.fuente(11),
                     text_color=tema.TENUE).grid(row=0, column=0, padx=(0, 8))
        self.sel_max = ctk.CTkOptionMenu(limite, values=list(self.LIMITES), width=130,
                                          font=tema.fuente(12), height=27,
                                          fg_color=tema.PANEL_2, button_color=tema.BORDE)
        self.sel_max.set("1 millón")
        self.sel_max.grid(row=0, column=1, sticky="ew")
        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.grid(row=3, column=0, sticky="ew", padx=12)
        acciones.grid_columnconfigure(0, weight=1)
        self.btn = ctk.CTkButton(acciones, text="Intentar ataque", width=140, height=28,
                                 fg_color=tema.EVE, hover_color="#c94455", text_color="#0b0f18",
                                 font=tema.fuente(12, "bold"), command=self._atacar)
        self.btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.btn_cancelar = ctk.CTkButton(acciones, text="Detener", width=85, height=28,
                                          fg_color=tema.PANEL_2, command=self._detener)
        self.btn_cancelar.grid(row=0, column=1)
        self.lbl_resultado = ctk.CTkLabel(self, text="", font=tema.fuente(11), height=44,
                                          width=1, wraplength=260, text_color=tema.TENUE,
                                          anchor="nw", justify="left")
        self.lbl_resultado.grid(row=4, column=0, sticky="ew", padx=12, pady=(8, 10))
        self.bind("<Configure>", lambda e: self.lbl_resultado.configure(
            wraplength=max(160, e.width / self._get_widget_scaling() - 24)), add="+")
        self.actualizar_publicos({})

    @property
    def datos_publicos(self):
        return dict(self._datos)

    @staticmethod
    def _objetivo(datos):
        return tuple(datos.get(k) for k in ("p", "g", "A"))

    def actualizar_publicos(self, datos):
        nuevos = {k: datos[k] for k in ("p", "g", "A", "B") if type(datos.get(k)) is int}
        cambio = self._objetivo(nuevos) != self._objetivo(self._datos)
        if cambio:
            self._invalidar()
            self._resultado = self._secreto = self._b_usada = None
        self._datos = nuevos
        for k, campo in self.campos.items():
            campo.set(nuevos.get(k))
        if cambio:
            self._emitir("esperando", intentos=0)
        if self._resultado and not self._resultado.cancelado and self._resultado.exponente is not None and "B" in nuevos:
            if nuevos["B"] != self._b_usada:
                self._derivar_con_b()
                self._mostrar_resultado()
        elif not self._buscando and self._resultado is None and self.estado["estado"] == "esperando":
            faltan = [k for k in ("p", "g", "A") if k not in nuevos]
            texto = (f"Esperando que pasen por el canal: {', '.join(faltan)}." if faltan
                     else "p, g y A capturados. Eve ya puede intentar encontrar a.")
            self.lbl_resultado.configure(text=texto, text_color=tema.TENUE)
        self._refrescar_controles()

    def bloquear_inicio(self, ocupado):
        self._canal_ocupado = ocupado
        self._refrescar_controles()

    def _refrescar_controles(self):
        listo = {"p", "g", "A"} <= self._datos.keys()
        texto_estado = {"esperando": "Lista para atacar" if listo else "Esperando datos",
                        "buscando": "Buscando…", "encontrada": "Exponente hallado",
                        "limite": "Límite alcanzado", "cancelado": "Detenida",
                        "error": "Error"}[self.estado["estado"]]
        self.chip.configure(text=f"● {texto_estado}")
        self.btn.configure(state="normal" if listo and not self._buscando and not self._canal_ocupado else "disabled",
                           text="Buscando…" if self._buscando else "Intentar ataque")
        self.sel_max.configure(state="disabled" if self._buscando else "normal")
        self.btn_cancelar.configure(state="normal" if self._buscando and not self._cancelacion.is_set() else "disabled")

    def _emitir(self, estado, **datos):
        self.estado = {"estado": estado, **datos}
        self.al_estado(dict(self.estado))

    def _atacar(self):
        if self._buscando or self._canal_ocupado or not {"p", "g", "A"} <= self._datos.keys():
            return
        self._invalidar()
        version = self._version
        cancelacion = self._cancelacion = threading.Event()
        p, g, publica = (self._datos[k] for k in ("p", "g", "A"))
        maximo = self.LIMITES[self.sel_max.get()]
        self._resultado = self._secreto = self._b_usada = None
        self._buscando = True
        ultimo = [0, 1]
        cerrojo = threading.Lock()

        def progreso(intentos, resto):
            with cerrojo:
                ultimo[:] = (intentos, resto)

        def trabajo():
            inicio = time.perf_counter()
            x, intentos = aritmetica.log_discreto_fuerza_bruta(
                g, publica, p, maximo, cancelado=cancelacion.is_set, al_progresar=progreso)
            return ResultadoBusqueda(x, intentos, time.perf_counter()-inicio, cancelacion.is_set())

        def listo(resultado):
            if version != self._version:
                return
            self._cancelar_sondeo()
            self._buscando = False
            self._resultado = resultado
            if not resultado.cancelado and resultado.exponente is not None:
                self._derivar_con_b()
            self._mostrar_resultado()
            self._refrescar_controles()

        def fallo(error):
            if version != self._version:
                return
            self._cancelar_sondeo()
            self._buscando = False
            self.lbl_resultado.configure(text=f"No se pudo completar el ataque: {error}", text_color=tema.EVE)
            self.al_registrar(f"Eve · error: {error}")
            self._emitir("error", intentos=0)
            self._refrescar_controles()

        def leer_progreso():
            self._sondeo_id = None
            if version != self._version or not self._buscando:
                return
            with cerrojo:
                intentos, resto = ultimo
            accion = "Deteniendo la búsqueda" if cancelacion.is_set() else "Eve está probando exponentes"
            self.lbl_resultado.configure(text=f"{accion} · {intentos:,} de {maximo:,} intentos reales.",
                                          text_color=tema.EVE)
            self._emitir("buscando", intentos=intentos, maximo=maximo, resto=resto)
            self._sondeo_id = self.after(60, leer_progreso)

        self.al_registrar(f"Eve inicia fuerza bruta sobre A={publica}, con p={p}, g={g}; límite {maximo:,}.")
        self._emitir("buscando", intentos=0, maximo=maximo, resto=1)
        self.lbl_resultado.configure(text="Eve está buscando…", text_color=tema.EVE)
        self._refrescar_controles()
        self._sondeo_id = self.after(60, leer_progreso)
        tema.correr_en_hilo(self, trabajo, listo, fallo)

    def _derivar_con_b(self):
        if "B" not in self._datos:
            return
        # Mismo motor modular que Alice y Bob, usando exclusivamente B pública
        # y el exponente que devolvió la búsqueda. No se lee su secreto.
        self._secreto, _ = aritmetica.mod_pow(self._datos["B"], self._resultado.exponente, self._datos["p"])
        self._b_usada = self._datos["B"]

    def _mostrar_resultado(self):
        r = self._resultado
        if r.cancelado:
            texto = f"Búsqueda detenida después de {r.intentos:,} intentos."
            estado, color = "cancelado", tema.TENUE
        elif r.exponente is None:
            texto = f"No encontró a en {r.intentos:,} intentos ({r.segundos:.2f} s). Se alcanzó el límite."
            estado, color = "limite", tema.AVISO
        else:
            texto = f"Eve encontró a = {r.exponente} en {r.intentos:,} intentos ({r.segundos:.2f} s)."
            texto += f" K = {self._secreto}." if self._secreto is not None else " Falta capturar B para calcular K."
            estado, color = "encontrada", tema.EVE
        self.lbl_resultado.configure(text=texto, text_color=color)
        self.al_registrar(f"Eve · {texto}")
        self._emitir(estado, intentos=r.intentos, exponente=r.exponente,
                      secreto=self._secreto, segundos=r.segundos)

    def _detener(self):
        if self._buscando:
            self._cancelacion.set()
            self.lbl_resultado.configure(text="Deteniendo la búsqueda…", text_color=tema.TENUE)
            self._refrescar_controles()

    def _cancelar_sondeo(self):
        if self._sondeo_id is not None:
            self.after_cancel(self._sondeo_id)
            self._sondeo_id = None

    def _invalidar(self):
        self._cancelacion.set()
        self._version += 1
        self._cancelar_sondeo()
        self._buscando = False

    def reiniciar(self):
        self._invalidar()
        self._datos = {}
        self._resultado = self._secreto = self._b_usada = None
        self.estado = {"estado": "esperando", "intentos": 0}
        self.actualizar_publicos({})

    def destroy(self):
        self._invalidar()
        super().destroy()
