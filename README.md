# REY — Software de Inventarios

Sistema de gestión de inventarios multibodega para el control de productos, ventas y movimientos. Desarrollado como proyecto del programa Análisis y Desarrollo de Software (SENA, ficha 3186627) para la empresa Perfumas.

## Tabla de contenidos

- [Descripción](#descripción)
- [Características](#características)
- [Tecnologías](#tecnologías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Variables de entorno](#variables-de-entorno)
- [Ejecución](#ejecución)
- [Roles](#roles)
- [Autores](#autores)

## Descripción

REY es una aplicación de escritorio para la administración de inventarios en múltiples bodegas (Fragancias, Bala Negra y General). Permite llevar el control de productos, registrar ventas con descuento automático del stock, reportar movimientos entre bodegas y generar reportes.

La aplicación funciona de forma local con PostgreSQL como base de datos principal y mantiene una copia en la nube mediante Supabase. La sincronización es local-first: los registros se guardan primero en la base local y se marcan como pendientes (`dirty = true`) hasta que se sincronizan con Supabase.

## Características

- Gestión de bodegas, productos, clientes y movimientos
- Registro de ventas con descuento automático de stock y detalle de venta
- Bitácora de auditoría para registrar acciones de los usuarios
- Reportes de inventario, ventas y movimientos
- Autenticación con roles (administrador / empleado)
- Sincronización local-first con Supabase mediante campos `dirty` y `synced_at`
- Modo escritorio y modo navegador, con cambio en caliente conservando la sesión
- Sesión persistente que se mantiene al cambiar entre modos

## Tecnologías

| Capa | Tecnología |
| --- | --- |
| Lenguaje | Python 3.12 |
| Interfaz | Flet (Flutter) |
| Base de datos local | PostgreSQL |
| Sincronización en la nube | Supabase (PostgREST) |
| Reportes | openpyxl / pandas |

## Estructura del proyecto

```
REY_SOFTWARE_DE_INVENTARIOS/
│
├── main.py                      # Punto de entrada
├── .env                         # Credenciales (no se sube a git)
├── .gitignore
├── README.md
├── requirements.txt
├── supabase_schema.sql          # Esquema de referencia para Supabase
├── start_rey.vbs                # Launcher para modo escritorio
├── start_rey_web.vbs            # Launcher para modo navegador
├── assets/
│   └── icon.ico                 # Icono de la aplicación
│
└── src/
    ├── core/
    │   ├── local_db.py          # Conexión a PostgreSQL local
    │   └── supabase_client.py   # Cliente de Supabase
    ├── models/
    │   └── user.py              # Modelo de usuario
    ├── services/                # Lógica de negocio (sin UI)
    │   ├── auth_service.py
    │   ├── bitacora_service.py
    │   ├── bodegas_service.py
    │   ├── clientes_service.py
    │   ├── movimientos_service.py
    │   ├── productos_service.py
    │   ├── reportes_service.py
    │   └── ventas_service.py
    ├── sync/
    │   └── sync_service.py      # Sincronización local ↔ Supabase
    ├── reports/
    │   ├── generators/          # Generación de reportes
    │   └── parsers/             # Transformación de datos
    ├── tests/
    │   ├── test_local_db.py
    │   └── test_supabase_connection.py
    └── ui/
        ├── app.py               # Router principal
        ├── components/          # Componentes reutilizables
        │   ├── cards.py
        │   ├── page_header.py
        │   ├── sidebar.py
        │   ├── status_header.py
        │   └── view_switcher.py
        └── views/               # Vistas de cada módulo
            ├── login_view.py
            ├── dashboard_view.py
            ├── bodegas_view.py
            ├── productos_view.py
            ├── movimientos_view.py
            ├── ventas_view.py
            ├── clientes_view.py
            ├── reportes_view.py
            └── bitacora_view.py
```

## Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/Santy2206/Rey_Software_de_inventarios.git
cd REY_Software_de_inventarios
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

Las tablas se crean automáticamente al primer arranque de la aplicación.

## Variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
SUPABASE_URL=https://<tu-proyecto>.supabase.co
SUPABASE_KEY=<tu-anon-key>

LOCAL_DB_HOST=127.0.0.1
LOCAL_DB_PORT=5432
LOCAL_DB_NAME=rey_inventarios
LOCAL_DB_USER=postgres
LOCAL_DB_PASSWORD=<tu-contraseña>
```

El archivo `.env` está incluido en `.gitignore` y no debe subirse al repositorio.

## Ejecución

Modo escritorio (ventana nativa):

```bash
python main.py
```

Modo navegador:

```bash
python main.py --web
```

Desde la interfaz se puede cambiar entre modos con el botón "Abrir en navegador" o "Abrir en escritorio". La sesión se mantiene al cambiar de modo.

Para sincronizar los datos locales con Supabase, usar el botón "Sincronizar ahora" en la barra de estado. Si hay registros pendientes, el badge mostrará "Pendientes (N)" en naranja.

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
