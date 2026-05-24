# 👑 REY — Software de Inventarios

> Sistema de gestión multibodega para el control eficiente de productos, ventas y movimientos entre las bodegas **Fragancias**, **Bala Negra** y **General**.

---

## 🗂️ Tabla de Contenidos

- [Descripción](#-descripción)
- [Características Principales](#-características-principales)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Variables de Entorno](#-variables-de-entorno)
- [Cómo Ejecutar](#-cómo-ejecutar)
- [Roles y Permisos](#-roles-y-permisos)
- [Autores](#-autores)

---

## 📋 Descripción

REY es una solución integral de escritorio diseñada para la administración eficiente de productos, ventas y movimientos entre múltiples bodegas. El sistema garantiza la **trazabilidad total** de las operaciones y la **integridad de los datos** en entornos de red local, con capacidad de sincronización en la nube mediante Supabase.

---

## 🚀 Características Principales

| Módulo                    | Descripción                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------ |
| **Gestión Multibodega**   | Control centralizado para las bodegas Fragancias, Bala Negra y General               |
| **Afectación Automática** | Registro de ventas con descuento automático del stock en la bodega correspondiente   |
| **Control de Bajas**      | Módulo para reportar productos dañados, caducados o ajustes por faltantes/sobrantes  |
| **Seguridad y Roles**     | Autenticación con niveles de acceso diferenciados para Administrador y Vendedor      |
| **Resiliencia de Datos**  | Operatividad en red local sin dependencia de internet, con sincronización en la nube |
| **Reportes Avanzados**    | Informes sobre valor del inventario, entradas, salidas y ventas                      |

---

## 🛠️ Stack Tecnológico

| Capa                          | Tecnología                                                |
| ----------------------------- | --------------------------------------------------------- |
| **Lenguaje**                  | Python 3.11+                                              |
| **Interfaz (UI)**             | [Flet](https://flet.dev/) (basado en Flutter)             |
| **Base de datos local**       | PostgreSQL — normalizada para concurrencia y consistencia |
| **Sincronización en la nube** | Supabase (PostgreSQL gestionado)                          |

---

## 📁 Estructura del Proyecto

```
REY_SOFTWARE_DE_INVENTARIOS/
│
├── main.py                         # Punto de entrada — solo llama ft.run()
├── .env                            # Credenciales (NO subir a git)
├── .gitignore
├── README.md
├── requirements.txt
│
└── src/
    ├── core/
    │   └── supabase_client.py      # Singleton de conexión a Supabase
    │
    ├── models/
    │   └── user.py                 # Modelo/esquema de usuario
    │
    ├── reports/
    │   ├── generators/             # Lógica para generar reportes
    │   └── parsers/                # Parseo y transformación de datos
    │
    ├── services/
    │   └── auth_service.py         # Lógica de autenticación (sin UI)
    │
    ├── sync/                       # Sincronización local ↔ nube
    │
    ├── tests/
    │   └── test_supabase_connection.py
    │
    └── ui/
        ├── app.py                  # Router principal y manejo de estado de página
        ├── components/
        │   └── cards.py            # Widgets reutilizables (tarjetas del dashboard)
        └── views/
            ├── login_view.py       # Pantalla de inicio de sesión
            └── dashboard_view.py   # Pantalla principal del dashboard
```

---

## ⚙️ Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/Santy2206/Rey_Software_de_inventarios.git
cd REY_Software_de_inventarios
```

### 2. Crear y activar el entorno virtual

```bash
# Windows #python 3.12
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## 🔐 Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
SUPABASE_URL=https://ojhnsyorsaowszkmfcmf.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qaG5zeW9yc2Fvd3N6a21mY21mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg0NDE5MDUsImV4cCI6MjA5NDAxNzkwNX0.IHGjm6TIBJuZ-VyhX0GSrFMRYJUNPgbQO8EnWFCFvRQ
```

> ⚠️ **Nunca subas el archivo `.env` a Git.** Ya está incluido en `.gitignore`.

---

## ▶️ Cómo Ejecutar

```bash
python main.py
```

La aplicación se abrirá en el navegador por defecto (`http://localhost:PORT`).

---

## 👥 Roles y Permisos

| Rol               | Acceso                                                            |
| ----------------- | ----------------------------------------------------------------- |
| **Administrador** | Acceso total: inventario, ventas, bajas, reportes y configuración |
| **Vendedor**      | Acceso restringido: solo registro de ventas y consulta de stock   |

---

## ✒️ Autores

Desarrollado por estudiantes de **Análisis y Desarrollo de Software** — SENA, ficha **3186627**:

- Laura Daniela Upegui Díaz
- Alison Gisell Nocua Cruz
- Jefferson Stiven Vargas Rodríguez
- Santiago Díaz Castellanos

---

_v2.0 © 2026 REY Inventarios_
