@echo off
setlocal
pushd "%~dp0"
set "DH_BUILD_PY=.venv-build\Scripts\python.exe"
if exist "%DH_BUILD_PY%" goto verificar
py -3.14 -c "import struct; assert struct.calcsize('P') == 8" >nul 2>&1
if not errorlevel 1 goto crear_py
python -c "import sys,struct; assert sys.version_info[:2] == (3,14) and struct.calcsize('P') == 8" >nul 2>&1
if errorlevel 1 goto falta_python
python -m venv .venv-build
goto verificar_creacion
:crear_py
py -3.14 -m venv .venv-build
:verificar_creacion
if errorlevel 1 goto error
:verificar
"%DH_BUILD_PY%" -c "import sys,struct; assert sys.version_info[:2] == (3,14) and struct.calcsize('P') == 8"
if errorlevel 1 goto falta_python
"%DH_BUILD_PY%" -m pip install -r requirements-build.txt
if errorlevel 1 goto error
"%DH_BUILD_PY%" herramientas\empaquetar_windows.py %*
if errorlevel 1 goto error
echo.
echo Listo. El archivo generado esta en dist; la ruta aparece arriba.
popd
pause
exit /b 0
:falta_python
echo.
echo Para GENERAR el exe se necesita Python 3.14 de 64 bits.
echo Instalalo y volve a abrir este script.
echo Para USAR la app, abri ejecutable\DiffieHellman-TP.exe: no necesita Python.
echo Si ya existe .venv-build, comproba que se haya creado con Python 3.14.
:error
echo.
echo No se pudo completar la generacion. Revisa el mensaje anterior.
popd
pause
exit /b 1
