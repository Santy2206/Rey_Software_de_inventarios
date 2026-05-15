"""
Conexión singleton a Supabase.

Lee SUPABASE_URL y SUPABASE_KEY desde el archivo .env y crea
una única instancia del cliente compartida en toda la aplicación.

Lanza:
    ValueError: Si alguna de las dos variables de entorno falta.

Uso:
    from src.core.supabase_client import supabase
    resultado = supabase.table("usuarios").select("*").execute()
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Faltan las credenciales de Supabase en el archivo .env")

supabase: Client = create_client(url, key)
