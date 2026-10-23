"""Colores, tipografías y helpers visuales compartidos por todas las vistas."""
import sys
import threading

import customtkinter as ctk

FONDO = "#0f1420"
PANEL = "#171d2b"
PANEL_2 = "#1f2738"
BORDE = "#2b3449"
TEXTO = "#e6e9ef"
TENUE = "#8a93a6"

ALICE = "#4f8cff"
BOB = "#2ec4a0"
EVE = "#ff5d6c"
OK = "#3ddc84"
AVISO = "#f5b041"

if sys.platform.startswith("win"):
    MONO = "Consolas"
elif sys.platform == "darwin":
    MONO = "Menlo"
else:
    MONO = "DejaVu Sans Mono"


def fuente(tam=13, peso="normal"):
    return ctk.CTkFont(size=tam, weight=peso)


def fuente_mono(tam=12):
    return ctk.CTkFont(family=MONO, size=tam)


def formatear(n: int | None, max_largo: int = 26) -> str:
    """Números enormes -> '123456…987654 (256 bits)'."""
    if n is None:
        return "—"
    s = str(n)
    if len(s) <= max_largo:
        return s
    return f"{s[:9]}…{s[-9:]}  ({n.bit_length()} bits)"


def correr_en_hilo(widget, fn, al_terminar, al_fallar):
    """Corre fn() en un hilo sin congelar la ventana y vuelve al hilo de Tk."""
    resultado = {}

    def trabajo():
        try:
            resultado["ok"] = fn()
        except Exception as e:  # se muestra en la GUI
            resultado["error"] = e

    hilo = threading.Thread(target=trabajo, daemon=True)
    hilo.start()

    def revisar():
        if hilo.is_alive():
            widget.after(60, revisar)
        elif "error" in resultado:
            al_fallar(resultado["error"])
        else:
            al_terminar(resultado["ok"])

    widget.after(60, revisar)
