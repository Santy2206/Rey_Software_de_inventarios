# REY — Software de Inventarios

Sistema de gestión de inventarios multibodega para el control de productos, ventas y movimientos. Desarrollado como proyecto del programa Análisis y Desarrollo de Software (SENA, ficha 3186627) para la empresa Perfumas.

## Tabla de contenidos

- [Descripción](#descripción)
- [Características](#características)
- [Tecnologías](#tecnologías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación para usuarios finales](#instalación-para-usuarios-finales)
- [Instalación para desarrolladores](#instalación-para-desarrolladores)
- [Variables de entorno](#variables-de-entorno)
- [Ejecución](#ejecución)
- [Construcción del instalador](#construcción-del-instalador)
- [Roles](#roles)
- [Autores](#autores)

## Descripción

REY es una aplicación de escritorio para la administración de inventarios en múltiples bodegas. Permite llevar el control de productos, registrar ventas con descuento automático del stock, reportar movimientos entre bodegas, generar reportes y sincronizar con Supabase.

La aplicación funciona de forma local con PostgreSQL como base de datos principal y puede sincronizar con Supabase. La sincronización es local-first: los registros se guardan primero en la base local y se marcan como pendientes (`dirty = true`) hasta que se sincronizan con la nube.

## Características

- Gestión de bodegas, productos, clientes y movimientos
- Registro de ventas con descuento automático de stock y detalle de venta
- Bitácora de auditoría para registrar acciones de los usuarios
- Reportes de inventario, ventas y movimientos en Excel
- Autenticación con roles (administrador / empleado)
- Sincronización local-first con Supabase mediante campos `dirty` y `synced_at`
- Modo escritorio y modo navegador

## Tecnologías

| Capa | Tecnología |
| --- | --- |
| Lenguaje | Python 3.12 |
| Interfaz | Flet (Flutter) |
| Base de datos local | PostgreSQL |
| Sincronización en la nube | Supabase (PostgREST) |
| Reportes | openpyxl / pandas |
| Instalador | Inno Setup 6 |

## Estructura del proyecto

```
REY_SOFTWARE_DE_INVENTARIOS/
│
├── main.py                      # Punto de entrada
├── .env                         # Credenciales (no se sube a git)
├── .gitignore
├── README.md
├── requirements.txt
├── start_rey.vbs                # Launcher desarrollo: modo escritorio
├── start_rey_web.vbs            # Launcher desarrollo: modo navegador
├── supabase_schema.sql          # Esquema de referencia para Supabase
├── assets/
│   ├── icon.ico                 # Icono de la aplicación (R + corona)
│   └── generar_icono.py         # Script para regenerar el icono
├── deploy/
│   ├── db/
│   │   ├── 01_schema.sql        # Schema de la base de datos local
│   │   ├── 02_seed.sql          # Datos iniciales de prueba
│   │   └── prueba_crud.sql      # Scripts de prueba
│   └── windows/
│       └── construir_ejecutable.bat  # Compila el .exe con flet pack
├── installer/
│   ├── REY_Setup.iss            # Script de Inno Setup
│   └── source/                  # Archivos empaquetados en el setup
│       ├── base_de_datos/       # 01_schema.sql, 02_seed.sql
│       ├── crear_bd.bat         # Crea/actualiza la base de datos
│       └── env.ejemplo          # Plantilla de variables de entorno
└── src/                         # Código fuente de la aplicación
    ├── core/
    ├── models/
    ├── services/
    ├── sync/
    ├── tests/
    └── ui/
```

## Instalación para usuarios finales

1. Descargue `dist/REY_Setup.exe` (no se incluye en el repositorio por su tamaño; se genera localmente).
2. Ejecute `REY_Setup.exe` como administrador.
3. El instalador hará lo siguiente:
   - Instalará PostgreSQL 16 en silencio si no está instalado (contraseña por defecto: `UDMVnxjZVgDT`).
   - Si PostgreSQL ya está instalado, pedirá la contraseña del usuario `postgres`. Tras 3 intentos fallidos ofrecerá reinstalar PostgreSQL con la contraseña por defecto.
   - Creará o recreará la base de datos `rey_inventarios` y el usuario `rey_user`.
   - Aplicará el schema y los datos de prueba.
   - Copiará la aplicación a `C:\Program Files\REY Inventarios`.
   - Creará el acceso directo en el Escritorio y el menú Inicio.
   - Ofrecerá abrir REY al finalizar.
4. Ingrese con uno de los usuarios de prueba:
   - `admin / admin123` (administrador)
   - `empleado / empleado123` (empleado)

> **Nota:** La reinstalación automática de PostgreSQL borra todas las bases de datos existentes en ese servidor.

## Instalación para desarrolladores

1. Clonar el repositorio:

```bash
git clone https://github.com/Santy2206/Rey_Software_de_inventarios.git
cd Rey_Software_de_inventarios
```

2. Crear y activar el entorno virtual (Python 3.12):

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Crear la base de datos local en PostgreSQL:

```sql
CREATE DATABASE rey_inventarios;
```

5. Crear el archivo `.env` en la raíz del proyecto (ver `installer/source/env.ejemplo` o la sección Variables de entorno).

6. Ejecutar la aplicación:

```bash
python main.py            # modo escritorio
python main.py --web      # modo navegador en http://localhost:8550
```

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto (no se sube a git):

```env
SUPABASE_URL=https://<tu-proyecto>.supabase.co
SUPABASE_KEY=<tu-anon-key>

LOCAL_DB_HOST=127.0.0.1
LOCAL_DB_PORT=5432
LOCAL_DB_NAME=rey_inventarios
LOCAL_DB_USER=rey_user
LOCAL_DB_PASSWORD=UDMVnxjZVgDT
```

> El instalador genera el `.env` automáticamente con los valores de `rey_user`.

## Ejecución

Modo escritorio (ventana nativa):

```bash
python main.py
```

Modo navegador:

```bash
python main.py --web
```

Para sincronizar los datos locales con Supabase, usar el botón "Sincronizar ahora" en la barra de estado.

## Construcción del instalador

1. Generar el ejecutable empaquetado:

```bash
.venv\Scripts\activate
flet pack main.py --name REY_Inventarios --icon assets/icon.ico --add-data "assets:assets" --onedir --pyinstaller-build-args="--collect-data=flet_web" --product-name "REY Inventarios" --file-description "Software de inventarios multibodega" --product-version 2.0.0 --file-version 2.0.0.0 --company-name "SENA ADSO Ficha 3186627" --copyright "2026 REY Inventarios" -y
```

2. Copiar el resultado al instalador:

```bash
xcopy /E /I /Y dist\REY_Inventarios installer\source\REY_Inventarios
```

3. Colocar `postgresql-win-x64.exe` en `installer/source/`. Se puede descargar de EnterpriseDB.

4. Compilar el setup con Inno Setup:

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\REY_Setup.iss
```

El instalador final se genera en `dist/REY_Setup.exe`.

## Icono

El icono de la aplicación (`assets/icon.ico`) muestra una **R roja sobre fondo dorado con una corona dorada arriba**. Para regenerarlo ejecute:

```bash
python assets/generar_icono.py
```

Luego debe recompilar el ejecutable y el instalador para que el cambio se aplique.

## Roles

| Rol | Permisos |
| --- | --- |
| Administrador | Acceso total: bodegas, productos, movimientos, ventas, clientes, reportes, bitácora |
| Empleado | Acceso restringido: ventas y consulta de inventario |

## Autores

Desarrollado por estudiantes de Análisis y Desarrollo de Software — SENA, ficha 3186627:

- Laura Daniela Upegui Díaz
- Alison Gisell Nocua Cruz
- Jefferson Stiven Vargas Rodríguez
- Santiago Díaz Castellanos
