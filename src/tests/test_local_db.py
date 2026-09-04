"""
Pruebas de integración para la conexión a PostgreSQL local.

Verifica que:
- Las credenciales de local_db.py cargan correctamente.
- El pool de conexiones se puede instanciar sin errores.
- Una consulta básica SELECT 1 retorna una respuesta válida.

Uso:
    pytest src/tests/test_local_db.py -v

Nota:
    Requiere un archivo .env válido con credenciales locales.
    Estas pruebas tocan la base de datos local — no ejecutar
    en integración continua (CI) sin configurar los secretos primero.
"""

from src.core.local_db import run_query


def test_connection():
    print("🔄 Intentando conectar a la base de datos local...")
    try:
        result = run_query("SELECT 1 AS uno")
        assert result is not None, "No se recibió respuesta de la base de datos."
        assert len(result) == 1, f"Se esperaba 1 fila, se recibieron {len(result)}."
        assert result[0]["uno"] == 1, f"Valor inesperado: {result[0]['uno']}."
        print("✅ ¡Conexión exitosa a Rey_inventarios_local desde psycopg2!")
    except Exception as e:
        print("❌ Error crítico al conectar a la base de datos local:")
        print(e)
        raise
