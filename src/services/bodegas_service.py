"""
Servicio de Bodegas — versión BASE DE DATOS LOCAL.

Maneja todas las operaciones de la tabla 'bodegas' en PostgreSQL local.
Mismo contrato que la versión anterior (Supabase):
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - Si hay datos, los incluye bajo la llave 'data'
  - SIN importaciones de Flet — solo lógica pura

El id se genera automáticamente en la base de datos (DEFAULT gen_random_uuid()),
así que nunca lo mandamos nosotros al hacer INSERT.

Tabla:
    bodegas (id, nombre, tipo, created_at, dirty, synced_at)
"""

from src.core.local_db import run_query


class BodegasService:

    @staticmethod
    def get_all():
        """Trae todas las bodegas de la base de datos."""
        print("--- Trayendo todas las bodegas ---")
        try:
            # 'ubicacion AS tipo' — bodegas_view.py espera la llave "tipo"
            data = run_query(
                "SELECT id, nombre, ubicacion AS tipo, creado_en "
                "FROM bodegas ORDER BY nombre"
            )

            if not data:
                print("⚠️ No hay bodegas registradas aún")
                return {"success": False, "message": "No hay bodegas registradas"}

            print(f"✅ Se encontraron {len(data)} bodega(s)")
            return {"success": True, "message": "Bodegas obtenidas", "data": data}

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en BodegasService.get_all: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener bodegas: {error_msg}",
            }

    @staticmethod
    def get_one(bodega_id: str):
        """
        Trae una sola bodega por su ID.

        Parámetros:
            bodega_id: el id de la bodega que queremos buscar
        """
        print(f"--- Buscando bodega con id: {bodega_id} ---")
        try:
            bodega = run_query(
                "SELECT id, nombre, ubicacion AS tipo, creado_en "
                "FROM bodegas WHERE id = %s",
                (bodega_id,),
                fetch_one=True,
            )

            if not bodega:
                print(f"⚠️ Bodega con id {bodega_id} no encontrada")
                return {"success": False, "message": "Bodega no encontrada"}

            print(f"✅ Bodega encontrada: {bodega['nombre']}")
            return {"success": True, "message": "Bodega encontrada", "data": bodega}

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en BodegasService.get_one: {error_msg}")
            return {"success": False, "message": f"Error al buscar bodega: {error_msg}"}

    @staticmethod
    def create(nombre: str, tipo: str):
        """
        Crea una nueva bodega.

        Parámetros:
            nombre: nombre de la bodega, ej: "Bodega Principal"
            tipo:   se guarda en la columna 'ubicacion' de la tabla real.
                    (el parámetro se sigue llamando 'tipo' para no romper
                    bodegas_view.py, que ya te llama con tipo=tipo)
        """
        print(f"--- Creando bodega: {nombre} ({tipo}) ---")
        try:
            bodega = run_query(
                """
                INSERT INTO bodegas (nombre, ubicacion)
                VALUES (%s, %s)
                RETURNING *
                """,
                (nombre, tipo),
                fetch_one=True,
            )

            if not bodega:
                return {"success": False, "message": "No se pudo crear la bodega"}

            print(f"✅ Bodega '{nombre}' creada con éxito")
            return {
                "success": True,
                "message": f"Bodega '{nombre}' creada con éxito",
                "data": bodega,
            }

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en BodegasService.create: {error_msg}")
            return {"success": False, "message": f"Error al crear bodega: {error_msg}"}

    @staticmethod
    def update(bodega_id: str, nombre: str, tipo: str):
        """
        Actualiza el nombre y/o tipo de una bodega existente.

        Parámetros:
            bodega_id: el id de la bodega a actualizar
            nombre:    nuevo nombre
            tipo:      nuevo tipo
        """
        print(f"--- Actualizando bodega id: {bodega_id} ---")
        try:
            bodega = run_query(
                """
                UPDATE bodegas
                SET nombre = %s, ubicacion = %s
                WHERE id = %s
                RETURNING *
                """,
                (nombre, tipo, bodega_id),
                fetch_one=True,
            )

            if not bodega:
                return {
                    "success": False,
                    "message": "Bodega no encontrada para actualizar",
                }

            print(f"✅ Bodega actualizada con éxito")
            return {
                "success": True,
                "message": "Bodega actualizada con éxito",
                "data": bodega,
            }

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en BodegasService.update: {error_msg}")
            return {
                "success": False,
                "message": f"Error al actualizar bodega: {error_msg}",
            }

    @staticmethod
    def delete(bodega_id: str):
        """
        Elimina una bodega por su ID.

        Parámetros:
            bodega_id: el id de la bodega a eliminar
        """
        print(f"--- Eliminando bodega id: {bodega_id} ---")
        try:
            eliminado = run_query(
                "DELETE FROM bodegas WHERE id = %s RETURNING id",
                (bodega_id,),
                fetch_one=True,
            )

            if not eliminado:
                return {
                    "success": False,
                    "message": "Bodega no encontrada para eliminar",
                }

            print(f"✅ Bodega eliminada con éxito")
            return {"success": True, "message": "Bodega eliminada con éxito"}

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en BodegasService.delete: {error_msg}")
            return {
                "success": False,
                "message": f"Error al eliminar bodega: {error_msg}",
            }
