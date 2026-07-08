import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# FORMA ULTRA-SEGURA DE BUSCAR EL .ENV DESDE LA RAÍZ DEL PROYECTO
# Como estás parado en 'Rey_Software_de_inventarios', buscamos el archivo ahí directamente
current_dir = Path.cwd()
env_path = current_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Obtener credenciales de la base local (Cambiamos el default a puerto 5432)
DB_HOST = os.getenv("LOCAL_DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("LOCAL_DB_PORT", "5432")
DB_NAME = os.getenv("LOCAL_DB_NAME", "rey_inventarios")
DB_USER = os.getenv("LOCAL_DB_USER", "postgres")
DB_PASSWORD = os.getenv("LOCAL_DB_PASSWORD")

# Imprimir para depuración (Esto nos dirá qué está leyendo Python)
print(f"🔍 DEBUG: Contraseña leída del .env: {'***' if DB_PASSWORD else 'VACÍA/NONE'}")
print(f"🔍 DEBUG: Intentando conectar a [{DB_USER}]@[{DB_HOST}]:{DB_PORT}/{DB_NAME}")

if not DB_PASSWORD:
    raise ValueError(
        "❌ ERROR: La variable LOCAL_DB_PASSWORD no está definida en el archivo .env"
    )

# Construir la URL de conexión
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_local_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
