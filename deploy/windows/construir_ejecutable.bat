@echo off
REM =====================================================================
REM  REY Inventarios - Generar ejecutable para Windows (REY_Inventarios.exe)
REM  Doble clic en este archivo. Resultado:
REM    dist\REY_Inventarios\REY_Inventarios.exe
REM    dist\REY_Inventarios_v2.0_Windows.zip   (paquete para Google Drive)
REM =====================================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0\..\.."
set ROOT=%CD%
set NOMBRE=REY_Inventarios
set PAQUETE=dist\%NOMBRE%_v2.0_Windows

echo.
echo [1/5] Verificando entorno virtual (.venv)...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || goto :error
)
call ".venv\Scripts\activate.bat"

echo [2/5] Instalando dependencias y PyInstaller...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt || goto :error
pip install pyinstaller || goto :error

echo [3/5] Empaquetando con flet pack (puede tardar varios minutos)...
if exist "dist\%NOMBRE%" rmdir /s /q "dist\%NOMBRE%"
flet pack main.py ^
  --name %NOMBRE% ^
  --icon assets\icon.ico ^
  --add-data "assets:assets" ^
  --onedir ^
  --pyinstaller-build-args="--collect-data=flet_web" ^
  --product-name "REY Inventarios" ^
  --file-description "Software de inventarios multibodega" ^
  --product-version 2.0.0 ^
  --file-version 2.0.0.0 ^
  --company-name "SENA ADSO Ficha 3186627" ^
  --copyright "2026 REY Inventarios" ^
  -y || goto :error

echo [4/5] Armando paquete de instalacion...
if exist "%PAQUETE%" rmdir /s /q "%PAQUETE%"
mkdir "%PAQUETE%\app" "%PAQUETE%\base_de_datos"
xcopy /e /i /q /y "dist\%NOMBRE%" "%PAQUETE%\app" >nul
copy /y deploy\db\01_schema.sql   "%PAQUETE%\base_de_datos\" >nul
copy /y deploy\db\02_seed.sql     "%PAQUETE%\base_de_datos\" >nul
copy /y deploy\db\prueba_crud.sql "%PAQUETE%\base_de_datos\" >nul
copy /y deploy\windows\instalar_rey.bat  "%PAQUETE%\" >nul
copy /y deploy\windows\crear_base_datos.bat "%PAQUETE%\" >nul
copy /y deploy\windows\env.ejemplo "%PAQUETE%\" >nul
copy /y deploy\windows\crear_accesos.ps1 "%PAQUETE%\" >nul
copy /y LEAME.txt "%PAQUETE%\" >nul

echo [5/5] Comprimiendo en ZIP...
if exist "%PAQUETE%.zip" del /q "%PAQUETE%.zip"
powershell -NoProfile -Command "Compress-Archive -Path '%PAQUETE%\*' -DestinationPath '%PAQUETE%.zip'" || goto :error

echo.
echo ==============================================================
echo  LISTO
echo  Ejecutable : %ROOT%\dist\%NOMBRE%\%NOMBRE%.exe
echo  Paquete    : %ROOT%\%PAQUETE%.zip   (subir a Google Drive)
echo ==============================================================
pause
exit /b 0

:error
echo.
echo *** Ocurrio un error. Revise los mensajes de arriba. ***
pause
exit /b 1
