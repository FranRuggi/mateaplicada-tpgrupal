"""Generar un exe único (predeterminado) o un ZIP con carpeta portable."""
import argparse
from datetime import datetime
import hashlib
from importlib import metadata
from pathlib import Path
import shutil
import struct
import subprocess
import sys


def preparar_documentacion(raiz, paquete, marca):
    shutil.copy2(raiz / "distribucion" / "COMO-JUGAR.txt", paquete)
    shutil.copy2(raiz / "GUIA-DE-ESTUDIO.md", paquete)
    (paquete / "docs").mkdir()
    shutil.copy2(raiz / "docs" / "CIFRADO.md", paquete / "docs")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=raiz, check=True,
                              text=True, capture_output=True).stdout.strip()
    cambios = subprocess.run(["git", "status", "--porcelain"], cwd=raiz, check=True,
                             text=True, capture_output=True).stdout.strip()
    estado = "con cambios sin commit" if cambios else "sin cambios locales"
    versiones = "\n".join(f"{p}={metadata.version(p)}" for p in
                            ("customtkinter", "websockets", "cryptography", "pyinstaller"))
    (paquete / "VERSION.txt").write_text(
        f"Diffie-Hellman - Windows 64 bits\nRevision: {revision}\nEstado: {estado}\n"
        f"Generado: {marca}\nPython: {sys.version}\n{versiones}\n", encoding="utf-8")
    licencias = paquete / "LICENCIAS"
    licencias.mkdir()
    licencia_python = Path(sys.base_prefix) / "LICENSE.txt"
    if licencia_python.exists():
        shutil.copy2(licencia_python, licencias / "Python.txt")
    for dependencia in ("customtkinter", "websockets", "darkdetect", "packaging",
                        "cryptography", "cffi", "pycparser"):
        distribucion = metadata.distribution(dependencia)
        for archivo in distribucion.files or ():
            if ".dist-info" in str(archivo) and "license" in str(archivo).lower():
                origen = Path(distribucion.locate_file(archivo))
                if origen.is_file():
                    shutil.copy2(origen, licencias / f"{dependencia}-{origen.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formato", choices=("archivo", "carpeta"), default="archivo",
                        help="archivo: exe único; carpeta: ZIP con _internal (formato anterior)")
    args = parser.parse_args()
    if sys.platform != "win32" or struct.calcsize("P") != 8:
        raise SystemExit("Este paquete se genera desde Windows con Python de 64 bits.")
    raiz = Path(__file__).resolve().parents[1]
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    nombre = "DiffieHellman-TP"
    destino = raiz / "dist" / marca
    trabajo = raiz / "build" / marca
    destino.mkdir(parents=True, exist_ok=False)
    trabajo.mkdir(parents=True, exist_ok=False)
    documentos = trabajo / "documentacion"
    documentos.mkdir()
    preparar_documentacion(raiz, documentos, marca)
    archivo_unico = args.formato == "archivo"
    comando = [
        sys.executable, "-m", "PyInstaller", "--onefile" if archivo_unico else "--onedir",
        "--windowed", "--noupx", "--name", nombre, "--collect-data", "customtkinter",
        "--collect-submodules", "websockets",
        "--add-data", f"{raiz / 'assets'}:assets",
        "--add-data", f"{raiz / 'configuracion.json'}:.",
        "--add-data", f"{documentos}:documentacion",
        "--specpath", str(trabajo), "--workpath", str(trabajo / "pyinstaller"),
        "--distpath", str(destino), str(raiz / "main.py"),
    ]
    subprocess.run(comando, cwd=raiz, check=True)
    if archivo_unico:
        entrega = destino / f"{nombre}.exe"
    else:
        paquete = destino / nombre
        shutil.copy2(raiz / "configuracion.json", paquete)
        shutil.copytree(documentos, paquete, dirs_exist_ok=True)
        entrega = Path(shutil.make_archive(
            str(raiz / "dist" / f"{nombre}-Windows-{marca}"), "zip",
            root_dir=destino, base_dir=nombre))
    with entrega.open("rb") as archivo:
        huella = hashlib.file_digest(archivo, "sha256").hexdigest()
    entrega.with_suffix(".sha256.txt").write_text(f"{huella}  {entrega.name}\n", encoding="ascii")
    print(f"\nArchivo para compartir: {entrega}")
    print(f"SHA-256: {huella}")


if __name__ == "__main__":
    main()
