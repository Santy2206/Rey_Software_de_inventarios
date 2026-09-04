from src.core.local_db import get_cursor

TABLAS = [
    "productos",
    "movimientos",
    "ventas",
    "bodegas",
    "clientes",
    "bitacora",
]

with get_cursor() as cur:
    for tabla in TABLAS:
        cur.execute(
            f"""
            ALTER TABLE {tabla}
            ADD COLUMN IF NOT EXISTS dirty BOOLEAN DEFAULT true,
            ADD COLUMN IF NOT EXISTS synced_at TIMESTAMP WITH TIME ZONE
            """
        )
        print(f"Columnas sync agregadas/verificadas en {tabla}")

print("Migración completada.")
