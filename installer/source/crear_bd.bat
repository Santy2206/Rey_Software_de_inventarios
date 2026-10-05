@echo off
REM =====================================================================
REM  REY Inventarios - Crear/actualizar base de datos local en PostgreSQL
REM  Parametro 1: contrasena del superusuario postgres.
REM  Si no se pasa, se usa UDMVnxjZVgDT (instalacion nueva/reinstalacion).
REM =====================================================================
chcp 65001 >nul
setlocal EnableDelayedExpansion
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

if not defined PSQL (
  echo ERROR: No se encontro PostgreSQL instalado. >>"%LOG%"
  exit /b 1
)

set "PGPASSWORD=%PGPASS%"
set "SCHEMA=%BASEPATH%base_de_datos\01_schema.sql"
set "SEED=%BASEPATH%base_de_datos\02_seed.sql"

REM Verificar conexion como postgres
"%PSQL%" -h localhost -U postgres -c "SELECT 1" >nul 2>>"%LOG%"
if errorlevel 1 (
  echo. >>"%LOG%"
  echo ERROR: No se pudo conectar a PostgreSQL como 'postgres'. >>"%LOG%"
  echo Verifique la contrasena e intente de nuevo. >>"%LOG%"
  exit /b 1
)

>>"%LOG%" echo Conexion a PostgreSQL verificada.

REM Crear o actualizar rol rey_user con contrasena fija
"%PSQL%" -h localhost -U postgres -v ON_ERROR_STOP=1 -c "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='rey_user') THEN CREATE ROLE rey_user LOGIN PASSWORD 'UDMVnxjZVgDT'; ELSE ALTER ROLE rey_user WITH PASSWORD 'UDMVnxjZVgDT'; END IF; END $$;" >>"%LOG%" 2>&1 || goto :error

REM Si la base de datos ya existe (instalacion previa), se preserva: NO se
REM elimina ni se recrea. Solo se vuelve a aplicar el schema (es idempotente,
REM usa IF NOT EXISTS) para traer tablas/columnas nuevas sin tocar los datos.
"%PSQL%" -h localhost -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='rey_inventarios'" | findstr 1 >nul
if not errorlevel 1 (
  >>"%LOG%" echo Base de datos existente detectada. Se preservan los datos; solo se actualiza el schema.
  "%PSQL%" -h localhost -U rey_user -d rey_inventarios -v ON_ERROR_STOP=1 -q -f "%SCHEMA%" >>"%LOG%" 2>&1 || goto :error
  >>"%LOG%" echo [%date% %time%] Base de datos actualizada (datos existentes preservados).
  exit /b 0
)

REM Primera instalacion: crear base de datos, schema y datos de ejemplo
"%PSQL%" -h localhost -U postgres -c "CREATE DATABASE rey_inventarios OWNER rey_user ENCODING 'UTF8' LC_COLLATE='es_CO.UTF-8' LC_CTYPE='es_CO.UTF-8' TEMPLATE template0;" >>"%LOG%" 2>&1 || goto :error

REM Crear tablas y datos iniciales como rey_user
"%PSQL%" -h localhost -U rey_user -d rey_inventarios -v ON_ERROR_STOP=1 -q -f "%SCHEMA%" >>"%LOG%" 2>&1 || goto :error
"%PSQL%" -h localhost -U rey_user -d rey_inventarios -v ON_ERROR_STOP=1 -q -f "%SEED%" >>"%LOG%" 2>&1 || goto :error

>>"%LOG%" echo [%date% %time%] Base de datos lista.
exit /b 0

:error
echo ERROR configurando la base de datos. Verifique %LOG%
exit /b 1
