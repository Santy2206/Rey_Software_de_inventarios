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
from src.services.auth_service import AuthService
from src.services.bitacora_service import BitacoraService


def _registrar_bitacora_clientes(detalle: dict):
    """Registra en bitácora sin afectar la operación principal."""
    try:
        usuario_id = AuthService.get_usuario_id()
        if usuario_id:
            BitacoraService.registrar(usuario_id, "CLIENTE", detalle)
    except Exception as e:
        print(f" Error al registrar bitácora de cliente: {e}")


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

            _registrar_bitacora_clientes(
                {
                    "descripcion": f"Cliente '{nombre_limpio}' creado",
                    "cliente_id": cliente["id"],
                    "nombre": nombre_limpio,
                    "telefono": telefono_limpio,
                    "email": email_limpio,
                }
            )

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

    @staticmethod
    def get_one(cliente_id: str):
        """Trae un cliente por su ID."""
        print(f"--- Buscando cliente con id: {cliente_id} ---")
        try:
            cliente = run_query(
                "SELECT id, nombre, telefono, email, creado_en "
                "FROM clientes WHERE id = %s",
                (cliente_id,),
                fetch_one=True,
            )

            if not cliente:
                return {"success": False, "message": "Cliente no encontrado"}

            print(f" Cliente encontrado: {cliente['nombre']}")
            return {
                "success": True,
                "message": "Cliente encontrado",
                "data": cliente,
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ClientesService.get_one: {error_msg}")
            return {
                "success": False,
                "message": f"Error al buscar cliente: {error_msg}",
            }

    @staticmethod
    def update(
        cliente_id: str,
        nombre: str,
        telefono: str = None,
        email: str = None,
    ):
        """
        Actualiza los datos de un cliente existente.

        Parámetros:
            cliente_id: id del cliente a actualizar
            nombre:     nuevo nombre
            telefono:   nuevo teléfono
            email:      nuevo correo
        """
        print(f"--- Actualizando cliente id: {cliente_id} ---")
        try:
            nombre_limpio = (nombre or "").strip()
            if not nombre_limpio:
                return {"success": False, "message": "El nombre del cliente es obligatorio"}

            telefono_limpio = (telefono or "").strip() or None
            email_limpio = (email or "").strip() or None

            cliente = run_query(
                """
                UPDATE clientes
                SET nombre = %s, telefono = %s, email = %s
                WHERE id = %s
                RETURNING *
                """,
                (nombre_limpio, telefono_limpio, email_limpio, cliente_id),
                fetch_one=True,
            )

            if not cliente:
                return {
                    "success": False,
                    "message": "Cliente no encontrado para actualizar",
                }

            _registrar_bitacora_clientes(
                {
                    "descripcion": f"Cliente '{nombre_limpio}' actualizado",
                    "cliente_id": cliente_id,
                    "nombre": nombre_limpio,
                    "telefono": telefono_limpio,
                    "email": email_limpio,
                }
            )

            print(f" Cliente actualizado con éxito")
            return {
                "success": True,
                "message": "Cliente actualizado con éxito",
                "data": cliente,
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ClientesService.update: {error_msg}")
            return {
                "success": False,
                "message": f"Error al actualizar cliente: {error_msg}",
            }

    @staticmethod
    def delete(cliente_id: str):
        """Elimina un cliente por su ID."""
        print(f"--- Eliminando cliente id: {cliente_id} ---")
        try:
            eliminado = run_query(
                "DELETE FROM clientes WHERE id = %s RETURNING id",
                (cliente_id,),
                fetch_one=True,
            )

            if not eliminado:
                return {
                    "success": False,
                    "message": "Cliente no encontrado para eliminar",
                }

            _registrar_bitacora_clientes(
                {
                    "descripcion": "Cliente eliminado",
                    "cliente_id": cliente_id,
                }
            )

            print(f" Cliente eliminado con éxito")
            return {"success": True, "message": "Cliente eliminado con éxito"}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ClientesService.delete: {error_msg}")
            return {
                "success": False,
                "message": f"Error al eliminar cliente: {error_msg}",
            }
