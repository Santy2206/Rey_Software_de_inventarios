from src.core.local_db import engine
from sqlalchemy import text


def test_connection():
    print("🔄 Intentando conectar a la base de datos local...")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1;"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ ¡Conexión exitosa a Rey_inventarios_local desde SQLAlchemy!")
            else:
                print("⚠️ La base de datos respondió, pero con un valor inesperado.")
    except Exception as e:
        print("❌ Error crítico al conectar a la base de datos local:")
        print(e)


if __name__ == "__main__":
    test_connection()
