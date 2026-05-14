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
