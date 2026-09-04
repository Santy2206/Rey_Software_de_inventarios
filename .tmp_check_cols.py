import os
from src.core.local_db import run_query

for tabla in ["productos", "movimientos", "ventas", "bodegas", "clientes", "bitacora"]:
    print(f"--- {tabla} ---")
    cols = run_query(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """,
        (tabla,)
    )
    for c in cols:
        print(f"  {c['column_name']}: {c['data_type']}")
