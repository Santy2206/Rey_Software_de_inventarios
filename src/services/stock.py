from .db import supabase


def get_stock():
    # Consulta la tabla de movimientos para calcular totales
    return supabase.table("movimientos_stock").select("*").execute()


def agregar_movimiento(bodega_id, producto_id, cantidad, tipo):
    data = {
        "bodega_id": bodega_id,
        "producto_id": producto_id,
        "cantidad": cantidad,
        "tipo": tipo,  # 'entrada' o 'salida'
    }
    return supabase.table("movimientos_stock").insert(data).execute()
