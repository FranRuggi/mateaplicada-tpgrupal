"""El exe único conserva Render sin necesitar un archivo externo."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from transporte.internet import url_predeterminada


class ConfiguracionIncluidaTests(unittest.TestCase):
    def test_configuracion_incluida_y_reemplazo_opcional_junto_al_exe(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            bundle, entrega = raiz / "bundle", raiz / "entrega"
            (bundle / "transporte").mkdir(parents=True)
            entrega.mkdir()
            (bundle / "configuracion.json").write_text('{"servidor_url":"https://incluido.test"}')
            with patch.dict(os.environ, {}, clear=True), patch("sys.frozen", True, create=True), \
                    patch("sys.executable", str(entrega / "app.exe")), \
                    patch("transporte.internet.__file__", str(bundle / "transporte" / "internet.py")):
                self.assertEqual(url_predeterminada(), "https://incluido.test")
                (entrega / "configuracion.json").write_text('{"servidor_url":"https://externo.test"}')
                self.assertEqual(url_predeterminada(), "https://externo.test")
                with patch.dict(os.environ, {"DH_SERVER_URL": "https://entorno.test"}):
                    self.assertEqual(url_predeterminada(), "https://entorno.test")
