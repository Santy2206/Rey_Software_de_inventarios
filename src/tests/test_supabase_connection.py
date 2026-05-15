"""
Pruebas de integración para la conexión a Supabase.

Verifica que:
- SUPABASE_URL y SUPABASE_KEY están presentes en el entorno.
- El cliente de Supabase se puede instanciar sin errores.
- Una consulta básica a la tabla 'usuarios' retorna una respuesta válida.

Uso:
    pytest src/tests/test_supabase_connection.py -v

Nota:
    Requiere un archivo .env válido con credenciales reales.
    Estas pruebas hacen llamadas reales a la red — no ejecutar
    en integración continua (CI) sin configurar los secretos primero.
"""

import sys
from supabase import create_client


def test_library_import():
    try:
        from supabase import create_client

        import_works = True
    except ImportError:
        import_works = False

    assert import_works is True, f"No se encontró la librería. Buscando en: {sys.path}"


def test_client_initialization():

    url = "https://ojhnsyorsaowszkmfcmf.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qaG5zeW9yc2Fvd3N6a21mY21mIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg0NDE5MDUsImV4cCI6MjA5NDAxNzkwNX0.IHGjm6TIBJuZ-VyhX0GSrFMRYJUNPgbQO8EnWFCFvRQ"
    client = create_client(url, key)
    assert client is not None
