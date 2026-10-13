@echo off
title GarajeData
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python. Instalalo desde https://www.python.org/downloads/
    echo y marca la opcion "Add python.exe to PATH" durante la instalacion.
    pause
    exit /b 1
)

python -c "import flask" >nul 2>nul
if errorlevel 1 (
    echo Instalando Flask por unica vez...
    python -m pip install -r requirements.txt
)

echo.
echo  GarajeData esta corriendo en http://127.0.0.1:5000
echo  Para apagarla, cerra esta ventana.
echo.

rem Abre el navegador cuando el servidor ya arranco.
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5000"

python app.py
pause
