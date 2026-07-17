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
                print(" No hay bodegas registradas aún")
                return {"success": False, "message": "No hay bodegas registradas"}

            print(f" Se encontraron {len(data)} bodega(s)")
            return {"success": True, "message": "Bodegas obtenidas", "data": data}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en BodegasService.get_all: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener bodegas: {error_msg}",
            }

    @staticmethod
    def get_one(bodega_id: str):
        """
        Trae una sola bodega por su ID.
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
                print(f"Bodega con id {bodega_id} no encontrada")
                return {"success": False, "message": "Bodega no encontrada"}

            print(f"Bodega encontrada: {bodega['nombre']}")
            return {"success": True, "message": "Bodega encontrada", "data": bodega}

        except Exception as e:
            error_msg = str(e)
            print(f"Error en BodegasService.get_one: {error_msg}")
            return {"success": False, "message": f"Error al buscar bodega: {error_msg}"}

    @staticmethod
    def create(nombre: str, tipo: str):
        """
        Crea una nueva bodega.
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

            print(f"Bodega '{nombre}' creada con éxito")
            return {
                "success": True,
                "message": f"Bodega '{nombre}' creada con éxito",
                "data": bodega,
            }

        except Exception as e:
            error_msg = str(e)
            print(f"Error en BodegasService.create: {error_msg}")
            return {"success": False, "message": f"Error al crear bodega: {error_msg}"}

    @staticmethod
    def update(bodega_id: str, nombre: str, tipo: str):
        """
        Actualiza el nombre y/o tipo de una bodega existente.
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

            print(f" Bodega actualizada con éxito")
            return {
                "success": True,
                "message": "Bodega actualizada con éxito",
                "data": bodega,
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en BodegasService.update: {error_msg}")
            return {
                "success": False,
                "message": f"Error al actualizar bodega: {error_msg}",
            }

    @staticmethod
    def delete(bodega_id: str):
        """
        Elimina una bodega por su ID.
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

            print(f" Bodega eliminada con éxito")
            return {"success": True, "message": "Bodega eliminada con éxito"}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en BodegasService.delete: {error_msg}")
            return {
                "success": False,
                "message": f"Error al eliminar bodega: {error_msg}",
            }
