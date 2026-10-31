"""Regresión: Tk 9 confunde el SVG de C2PA con los píxeles de la hoja PNG."""
from pathlib import Path
import struct
import unittest

import customtkinter as ctk

from gui.escena import EscenaIntercambio
from gui.vistas.internet import VistaInternet


class PersonajesPngTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ctk.CTk()
        cls.root.withdraw()
        cls.png = (Path(__file__).resolve().parents[1] / "assets" / "personajes-arcade.png").read_bytes()
        cls.ancho, cls.alto = struct.unpack(">II", cls.png[16:24])

    @classmethod
    def tearDownClass(cls):
        for identificador in cls.root.tk.call("after", "info"):
            cls.root.tk.call("after", "cancel", identificador)
        cls.root.destroy()

    def test_escena_carga_los_pixeles_png_y_recorta_tres_personajes_completos(self):
        escena = EscenaIntercambio(self.root)
        try:
            self.assertEqual((escena._hoja.width(), escena._hoja.height()), (self.ancho, self.alto))
            self.assertEqual(self.ancho, 3 * self.alto)
            for personaje in ("Alice", "Eve", "Bob"):
                sprite = escena._sprite(personaje, 140)
                self.assertEqual(sprite.width(), sprite.height())
        finally:
            escena.destroy()

    def test_tarjetas_de_sala_muestran_las_celdas_png_y_no_el_logo_svg(self):
        vista = VistaInternet(self.root)
        try:
            self.assertEqual(len(vista._imagenes), 2)
            esperado = (self.alto + 3) // 4
            for imagen in vista._imagenes:
                self.assertEqual((imagen.width(), imagen.height()), (esperado, esperado))
        finally:
            vista.destroy()
