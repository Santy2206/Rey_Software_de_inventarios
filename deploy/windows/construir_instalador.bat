@echo off
REM =====================================================================
REM  REY Inventarios - Generar el instalador final (Inno Setup)
REM  Doble clic en este archivo. Pasos:
REM    1. Reempaqueta la app con flet pack (dist\REY_Inventarios)
REM    2. Limpia cualquier sesion de login filtrada en el build
REM    3. Copia el build a installer\source\REY_Inventarios
REM    4. Compila installer\REY_Setup.iss con Inno Setup (ISCC)
REM  Resultado: dist\REY_Setup.exe
REM =====================================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0\..\.."
set ROOT=%CD%
set NOMBRE=REY_Inventarios

echo.
echo [1/4] Verificando entorno virtual (.venv)...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || goto :error
)
call ".venv\Scripts\activate.bat"

echo [2/4] Empaquetando con flet pack (puede tardar varios minutos)...
if exist "dist\%NOMBRE%" rmdir /s /q "dist\%NOMBRE%"
flet pack main.py ^
  --name %NOMBRE% ^
  --icon assets\icon.ico ^
  --add-data "assets:assets" ^
  --onedir ^
  --pyinstaller-build-args="--collect-data=flet_web" ^
  --product-name "REY Software de Inventarios" ^
  --file-description "REY Software de Inventarios" ^
  --product-version 2.0.0 ^
  --file-version 2.0.0.0 ^
  --company-name "SENA ADSO Ficha 3186627" ^
  --copyright "2026 REY Inventarios" ^
  -y || goto :error

REM Si se probo el .exe empaquetado en esta maquina, Flet guarda la sesion
REM de login junto al ejecutable (dentro de _internal). No debe distribuirse.
if exist "dist\%NOMBRE%\_internal\.rey_session.json" del /q "dist\%NOMBRE%\_internal\.rey_session.json"

echo [3/4] Copiando build a installer\source\%NOMBRE%...
if exist "installer\source\%NOMBRE%" rmdir /s /q "installer\source\%NOMBRE%"
xcopy /e /i /q /y "dist\%NOMBRE%" "installer\source\%NOMBRE%" >nul

echo [4/4] Compilando instalador con Inno Setup...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    echo ERROR: No se encontro ISCC.exe de Inno Setup 6. Instalalo desde https://jrsoftware.org/isdl.php
    goto :error
)
%ISCC% "installer\REY_Setup.iss" || goto :error

echo.
echo ==============================================================
echo  LISTO
echo  Instalador: %ROOT%\dist\REY_Setup.exe
echo ==============================================================
pause
exit /b 0

:error
echo.
echo *** Ocurrio un error. Revise los mensajes de arriba. ***
pause
exit /b 1
