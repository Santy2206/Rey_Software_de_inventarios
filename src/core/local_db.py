"""
Conexión a la base de datos LOCAL (PostgreSQL).

Reemplaza a supabase_client.py como fuente principal de datos de la app.
supabase_client.py NO se elimina — se seguirá usando más adelante en
sync_service.py para sincronizar hacia la nube.

Uso típico desde un service:

    from src.core.local_db import run_query, get_cursor

    # Consulta simple (SELECT, o INSERT/UPDATE/DELETE con RETURNING)
    productos = run_query("SELECT * FROM productos")
    producto  = run_query("SELECT * FROM productos WHERE id = %s", (id,), fetch_one=True)

    # Operación de varios pasos que deben tener éxito juntos o fallar juntos
    with get_cursor() as cur:
        cur.execute("SELECT stock FROM productos WHERE id = %s FOR UPDATE", (id,))
        ...
        cur.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo, id))

Variables de entorno esperadas en .env:
    LOCAL_DB_HOST     (opcional, por defecto "localhost")
    LOCAL_DB_PORT     (opcional, por defecto "5432")
    LOCAL_DB_NAME
    LOCAL_DB_USER
    LOCAL_DB_PASSWORD
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

load_dotenv()

_host = os.environ.get("LOCAL_DB_HOST", "localhost")
_port = os.environ.get("LOCAL_DB_PORT", "5432")
_dbname = os.environ.get("LOCAL_DB_NAME")
_user = os.environ.get("LOCAL_DB_USER")
_password = os.environ.get("LOCAL_DB_PASSWORD")

if not _dbname or not _user or not _password:
    raise ValueError(
        "Faltan las credenciales de la base de datos local en el archivo .env "
        "(LOCAL_DB_NAME, LOCAL_DB_USER, LOCAL_DB_PASSWORD)"
    )

# Pool de conexiones: evita abrir/cerrar una conexión nueva en cada consulta
# y permite que varios hilos (threading.Thread) trabajen sin chocar entre sí.
_pool = pool.SimpleConnectionPool(
    1,
    10,
    host=_host,
    port=_port,
    dbname=_dbname,
    user=_user,
    password=_password,
)


@contextmanager
def get_cursor():
    """
    Entrega un cursor listo para usar dentro de un 'with'.

    Al salir del bloque SIN errores, hace commit automáticamente.
    Si algo lanza una excepción adentro, hace rollback antes de propagarla,
    así nunca queda una operación a medias (ej: insertar un movimiento
    pero no alcanzar a actualizar el stock).

    Úsalo cuando necesites varias operaciones atómicas juntas.
    Para una sola consulta, usa run_query() — es más simple.
    """
    conn = _pool.getconn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        _pool.putconn(conn)


def run_query(query: str, params: tuple = None, fetch_one: bool = False):
    """
    Ejecuta UNA sola consulta SQL y retorna el resultado.

    - SELECT ...                              → lista de dicts
    - INSERT/UPDATE/DELETE ... RETURNING ...  → lista de dicts
    - INSERT/UPDATE/DELETE sin RETURNING      → None

    Parámetros:
        query:     sentencia SQL con placeholders %s (nunca uses f-strings
                   para meter valores directamente — eso es inyección SQL)
        params:    tupla de valores para los placeholders, ej: (id,)
        fetch_one: True si esperas un solo resultado (ej: buscar por id)
    """
    with get_cursor() as cur:
        cur.execute(query, params or ())
        if cur.description is None:
            return None
        rows = cur.fetchall()

    if fetch_one:
        return rows[0] if rows else None
    return rows
