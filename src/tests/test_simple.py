import sys

try:
    from supabase import create_client

    print("✅ ¡Librería encontrada con éxito!")
except ImportError:
    print("❌ Sigo sin encontrar la librería.")
    print(f"Buscando en: {sys.path}")
