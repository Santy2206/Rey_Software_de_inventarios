"""
Servicio de Bodegas.

Maneja todas las operaciones de la tabla 'bodegas' en Supabase.
Sigue el mismo patrón que auth_service.py:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - Si hay datos, los incluye bajo la llave 'data'
  - SIN importaciones de Flet — solo lógica pura

Tabla esperada en Supabase:
    bodegas (id, nombre, tipo)
"""

from src.core.supabase_client import supabase


class BodegasService:

    @staticmethod
    def get_all():
        """Trae todas las bodegas de la base de datos."""
        print("--- Trayendo todas las bodegas ---")
        try:
            res = supabase.table("bodegas").select("*").execute()

            if not res.data:
                print("⚠️ No hay bodegas registradas aún")
                return {"success": False, "message": "No hay bodegas registradas"}

            print(f"✅ Se encontraron {len(res.data)} bodega(s)")
            return {"success": True, "message": "Bodegas obtenidas", "data": res.data}

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
            res = (
                supabase.table("bodegas")
                .select("*")
                .eq("id", bodega_id)
                .maybe_single()
                .execute()
            )

            if not res.data:
                print(f"⚠️ Bodega con id {bodega_id} no encontrada")
                return {"success": False, "message": "Bodega no encontrada"}

            print(f"✅ Bodega encontrada: {res.data['nombre']}")
            return {"success": True, "message": "Bodega encontrada", "data": res.data}

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
            tipo:   tipo de bodega, ej: "Fragancias", "Bala Negra", "General"
        """
        print(f"--- Creando bodega: {nombre} ({tipo}) ---")
        try:
            nueva_bodega = {"nombre": nombre, "tipo": tipo}

            res = supabase.table("bodegas").insert(nueva_bodega).execute()

            if not res.data:
                return {"success": False, "message": "No se pudo crear la bodega"}

            print(f"✅ Bodega '{nombre}' creada con éxito")
            return {
                "success": True,
                "message": f"Bodega '{nombre}' creada con éxito",
                "data": res.data[0],
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
            datos_actualizados = {"nombre": nombre, "tipo": tipo}

            res = (
                supabase.table("bodegas")
                .update(datos_actualizados)
                .eq("id", bodega_id)
                .execute()
            )

            if not res.data:
                return {
                    "success": False,
                    "message": "Bodega no encontrada para actualizar",
                }

            print(f"✅ Bodega actualizada con éxito")
            return {
                "success": True,
                "message": "Bodega actualizada con éxito",
                "data": res.data[0],
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
            res = supabase.table("bodegas").delete().eq("id", bodega_id).execute()

            if not res.data:
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
