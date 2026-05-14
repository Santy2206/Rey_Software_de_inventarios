from .db import supabase


def listar_productos():
    """Trae la lista completa de productos"""
    return supabase.table("productos").select("*").execute()


def buscar_producto_por_sku(sku):
    """Busca un producto específico por su código único"""
    return (
        supabase.table("productos").select("*").eq("sku", sku).maybe_single().execute()
    )
