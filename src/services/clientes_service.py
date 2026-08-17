"""
Servicio de Clientes — base de datos local.

Tabla:
    clientes (id, nombre, telefono, email, creado_en)

Mismo contrato que el resto de servicios:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - Si hay datos, los incluye bajo la llave 'data'
  - SIN importaciones de Flet — solo lógica pura
"""

from src.core.local_db import run_query


class ClientesService:

    @staticmethod
    def get_all():
        """Trae todos los clientes ordenados por nombre."""
        print("--- Trayendo todos los clientes ---")
        try:
            data = run_query(
                "SELECT id, nombre, telefono, email, creado_en "
                "FROM clientes ORDER BY nombre"
            )

            if not data:
                return {"success": False, "message": "No hay clientes registrados"}

            print(f" Se encontraron {len(data)} cliente(s)")
            return {"success": True, "message": "Clientes obtenidos", "data": data}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ClientesService.get_all: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener clientes: {error_msg}",
            }

    @staticmethod
    def create(nombre: str, telefono: str = None, email: str = None):
        """
        Crea un cliente nuevo.

        Parámetros:
            nombre:   nombre del cliente (obligatorio)
            telefono: teléfono de contacto (opcional)
            email:    correo (opcional)
        """
        print(f"--- Creando cliente: {nombre} ---")
        try:
            nombre_limpio = (nombre or "").strip()
            if not nombre_limpio:
                return {"success": False, "message": "El nombre del cliente es obligatorio"}

            telefono_limpio = (telefono or "").strip() or None
            email_limpio = (email or "").strip() or None

            cliente = run_query(
                """
                INSERT INTO clientes (nombre, telefono, email)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (nombre_limpio, telefono_limpio, email_limpio),
                fetch_one=True,
            )

            if not cliente:
                return {"success": False, "message": "No se pudo crear el cliente"}

            print(f" Cliente '{nombre_limpio}' creado con exito")
            return {
                "success": True,
                "message": f"Cliente '{nombre_limpio}' creado con éxito",
                "data": cliente,
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ClientesService.create: {error_msg}")
            return {
                "success": False,
                "message": f"Error al crear cliente: {error_msg}",
            }
