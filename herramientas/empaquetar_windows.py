"""Generar un ZIP portable sin reemplazar versiones anteriores."""
from datetime import datetime
import hashlib
from importlib import metadata
from pathlib import Path
import shutil
import struct
import subprocess
import sys


def main():
    if sys.platform != "win32" or struct.calcsize("P") != 8:
        raise SystemExit("Este paquete se genera desde Windows con Python de 64 bits.")
    raiz = Path(__file__).resolve().parents[1]
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    nombre = "DiffieHellman-TP"
    destino = raiz / "dist" / marca
    trabajo = raiz / "build" / marca
    destino.mkdir(parents=True, exist_ok=False)
    trabajo.mkdir(parents=True, exist_ok=False)
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--onedir", "--windowed", "--noupx",
        "--name", nombre, "--collect-data", "customtkinter",
        "--collect-submodules", "websockets",
        "--add-data", f"{raiz / 'assets'}:assets",
        "--specpath", str(trabajo), "--workpath", str(trabajo / "pyinstaller"),
        "--distpath", str(destino), str(raiz / "main.py"),
    ], cwd=raiz, check=True)
    paquete = destino / nombre
    shutil.copy2(raiz / "configuracion.json", paquete)
    shutil.copy2(raiz / "distribucion" / "COMO-JUGAR.txt", paquete)
    shutil.copy2(raiz / "GUIA-DE-ESTUDIO.md", paquete)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=raiz, check=True,
                              text=True, capture_output=True).stdout.strip()
    versiones = "\n".join(f"{p}={metadata.version(p)}" for p in
                            ("customtkinter", "websockets", "pyinstaller"))
    (paquete / "VERSION.txt").write_text(
        f"Diffie-Hellman - Windows 64 bits\nRevision: {revision}\n"
        f"Generado: {marca}\nPython: {sys.version}\n{versiones}\n", encoding="utf-8")
    licencias = paquete / "LICENCIAS"
    licencias.mkdir()
    licencia_python = Path(sys.base_prefix) / "LICENSE.txt"
    if licencia_python.exists():
        shutil.copy2(licencia_python, licencias / "Python.txt")
    for dependencia in ("customtkinter", "websockets", "darkdetect", "packaging"):
        distribucion = metadata.distribution(dependencia)
        for archivo in distribucion.files or ():
            if ".dist-info" in str(archivo) and "license" in str(archivo).lower():
                origen = Path(distribucion.locate_file(archivo))
                if origen.is_file():
                    shutil.copy2(origen, licencias / f"{dependencia}-{origen.name}")
    zip_path = Path(shutil.make_archive(
        str(raiz / "dist" / f"{nombre}-Windows-{marca}"), "zip",
        root_dir=destino, base_dir=nombre))
    with zip_path.open("rb") as archivo_zip:
        huella = hashlib.file_digest(archivo_zip, "sha256").hexdigest()
    zip_path.with_suffix(".sha256.txt").write_text(f"{huella}  {zip_path.name}\n", encoding="ascii")
    print(f"\nEjecutable: {paquete / (nombre + '.exe')}")
    print(f"ZIP para compartir: {zip_path}")
    print(f"SHA-256: {huella}")


if __name__ == "__main__":
    main()
