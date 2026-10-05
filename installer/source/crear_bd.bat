@echo off
REM =====================================================================
REM  REY Inventarios - Crear/actualizar base de datos local en PostgreSQL
REM  Parametro 1: contrasena del superusuario postgres.
REM  Si no se pasa, se usa UDMVnxjZVgDT (instalacion nueva/reinstalacion).
REM
REM  Flujo lineal con "goto" a etiquetas en vez de bloques if(...) anidados:
REM  mezclar goto/exit dentro de bloques if(...) con parentesis es fragil
REM  en cmd.exe y puede romper el parser sin aviso claro.
REM =====================================================================
chcp 65001 >nul
set "BASEPATH=%~dp0"
cd /d "%BASEPATH%"
set "LOG=%BASEPATH%crear_bd.log"

set "PGPASS=%~1"
if "%PGPASS%"=="" set "PGPASS=UDMVnxjZVgDT"

>"%LOG%" echo [%date% %time%] Iniciando configuracion de la base de datos...

set "PSQL="
for %%V in (18 17 16 15 14) do (
  if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" if not defined PSQL set "PSQL=C:\Program Files\PostgreSQL\%%V\bin\psql.exe"
  if exist "C:\Program Files (x86)\PostgreSQL\%%V\bin\psql.exe" if not defined PSQL set "PSQL=C:\Program Files (x86)\PostgreSQL\%%V\bin\psql.exe"
)
if not defined PSQL goto :no_postgres

set "PGPASSWORD=%PGPASS%"
set "SCHEMA=%BASEPATH%base_de_datos\01_schema.sql"
set "SEED=%BASEPATH%base_de_datos\02_seed.sql"
set "TMP_OUT=%TEMP%\rey_crear_bd_%RANDOM%.tmp"

REM Verificar conexion como postgres
"%PSQL%" -h localhost -U postgres -c "SELECT 1" >nul 2>>"%LOG%"
if errorlevel 1 goto :no_connection

>>"%LOG%" echo Conexion a PostgreSQL verificada.

REM Crear o actualizar rol rey_user con contrasena fija
"%PSQL%" -h localhost -U postgres -v ON_ERROR_STOP=1 -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='rey_user') THEN CREATE ROLE rey_user LOGIN PASSWORD 'UDMVnxjZVgDT'; ELSE ALTER ROLE rey_user WITH PASSWORD 'UDMVnxjZVgDT'; END IF; END $$;" >>"%LOG%" 2>&1
if errorlevel 1 goto :error

REM Si la base de datos ya existe (instalacion previa), se preserva: NO se
REM elimina ni se recrea. Solo se vuelve a aplicar el schema (es idempotente,
REM usa IF NOT EXISTS) para traer tablas/columnas nuevas sin tocar los datos.
REM NOTA: ni "psql | findstr" ni "for /f ('comando')" son confiables aqui -
REM al correr sin consola interactiva (como lo hace el instalador) ambos
REM patrones pueden fallar o colgarse sin dejar rastro en el log. En su lugar
REM se redirige la salida de psql a un archivo temporal y se lee ese archivo
REM con "for /f", que si es confiable en este contexto.
>>"%LOG%" echo Verificando si la base de datos rey_inventarios ya existe...
"%PSQL%" -h localhost -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='rey_inventarios'" >"%TMP_OUT%" 2>>"%LOG%"
set "DB_EXISTS="
for /f "usebackq delims=" %%R in ("%TMP_OUT%") do set "DB_EXISTS=%%R"
del "%TMP_OUT%" >nul 2>&1

if "%DB_EXISTS%"=="1" goto :actualizar_existente

REM ---- Primera instalacion: crear base de datos, schema y datos de ejemplo ----
>>"%LOG%" echo Base de datos no encontrada. Creando instalacion nueva...
"%PSQL%" -h localhost -U postgres -c "CREATE DATABASE rey_inventarios OWNER rey_user ENCODING 'UTF8' LC_COLLATE='es_CO.UTF-8' LC_CTYPE='es_CO.UTF-8' TEMPLATE template0;" >>"%LOG%" 2>&1
if errorlevel 1 goto :error

>>"%LOG%" echo Aplicando schema...
"%PSQL%" -h localhost -U rey_user -d rey_inventarios -v ON_ERROR_STOP=1 -q -f "%SCHEMA%" >>"%LOG%" 2>&1
if errorlevel 1 goto :error

>>"%LOG%" echo Sembrando datos iniciales...
"%PSQL%" -h localhost -U rey_user -d rey_inventarios -v ON_ERROR_STOP=1 -q -f "%SEED%" >>"%LOG%" 2>&1
if errorlevel 1 goto :error

>>"%LOG%" echo [%date% %time%] Base de datos lista.
exit /b 0

:actualizar_existente
>>"%LOG%" echo Base de datos existente detectada. Se preservan los datos; solo se actualiza el schema.
"%PSQL%" -h localhost -U rey_user -d rey_inventarios -v ON_ERROR_STOP=1 -q -f "%SCHEMA%" >>"%LOG%" 2>&1
if errorlevel 1 goto :error

REM Si la base quedo vacia, por ejemplo una instalacion anterior que fallo
REM antes de sembrar los datos, se completa con los datos de ejemplo. Si ya
REM tiene usuarios reales, se deja intacta.
"%PSQL%" -h localhost -U rey_user -d rey_inventarios -tAc "SELECT count(*) FROM usuarios" >"%TMP_OUT%" 2>>"%LOG%"
set "USUARIOS_COUNT="
for /f "usebackq delims=" %%N in ("%TMP_OUT%") do set "USUARIOS_COUNT=%%N"
del "%TMP_OUT%" >nul 2>&1

if not "%USUARIOS_COUNT%"=="0" goto :actualizado_ok

>>"%LOG%" echo La tabla usuarios esta vacia, instalacion anterior incompleta. Sembrando datos iniciales.
"%PSQL%" -h localhost -U rey_user -d rey_inventarios -v ON_ERROR_STOP=1 -q -f "%SEED%" >>"%LOG%" 2>&1
if errorlevel 1 goto :error

:actualizado_ok
>>"%LOG%" echo [%date% %time%] Base de datos actualizada (datos existentes preservados).
exit /b 0

:no_postgres
>>"%LOG%" echo ERROR: No se encontro PostgreSQL instalado.
echo ERROR: No se encontro PostgreSQL instalado. Verifique %LOG%
exit /b 1

:no_connection
>>"%LOG%" echo.
>>"%LOG%" echo ERROR: No se pudo conectar a PostgreSQL como 'postgres'.
>>"%LOG%" echo Verifique la contrasena e intente de nuevo.
echo ERROR: No se pudo conectar a PostgreSQL. Verifique %LOG%
exit /b 1

:error
>>"%LOG%" echo [%date% %time%] ERROR: la configuracion de la base de datos se detuvo en el paso anterior.
echo ERROR configurando la base de datos. Verifique %LOG%
exit /b 1
