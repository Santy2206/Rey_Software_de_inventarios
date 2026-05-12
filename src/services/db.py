import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

if __name__ == "__main__":
    try:
        res = supabase.table("productos").select("*", count="exact").limit(1).execute()
        print("✅ Conexión exitosa a Supabase")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
