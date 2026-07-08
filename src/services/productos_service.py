"""
Servicio de Productos.

Maneja todas las operaciones de la tabla 'productos' en Supabase.
Sigue el mismo patrón que auth_service.py:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - Si hay datos, los incluye bajo la llave 'data'
  - SIN importaciones de Flet — solo lógica pura

Tabla esperada en Supabase:
    productos (id, nombre, tipo, funcion, unidad_medida, stock, bodega_id)

    unidad_medida solo puede ser: "gr" o "u"
"""

from src.core.supabase_client import supabase

UNIDADES_VALIDAS = ["gr", "u"]


class ProductosService:

    @staticmethod
    def get_all():
        """
        Trae todos los productos.
        Incluye la información de la bodega a la que pertenece cada uno.
        """
        print("--- Trayendo todos los productos ---")
        try:
            res = supabase.table("productos").select("*, bodegas(nombre)").execute()

            if not res.data:
                print("⚠️ No hay productos registrados aún")
                return {"success": False, "message": "No hay productos registrados"}

            print(f" Se encontraron {len(res.data)} producto(s)")
            return {"success": True, "message": "Productos obtenidos", "data": res.data}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ProductosService.get_all: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener productos: {error_msg}",
            }

    @staticmethod
    def get_by_bodega(bodega_id: str):
        """
        Trae todos los productos que pertenecen a una bodega específica.

        Parámetros:
            bodega_id: el id de la bodega que queremos filtrar
        """
        print(f"--- Trayendo productos de bodega: {bodega_id} ---")
        try:
            res = (
                supabase.table("productos")
                .select("*")
                .eq("bodega_id", bodega_id)
                .execute()
            )

            if not res.data:
                return {"success": False, "message": "No hay productos en esta bodega"}

            print(f" Se encontraron {len(res.data)} producto(s) en la bodega")
            return {"success": True, "message": "Productos obtenidos", "data": res.data}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ProductosService.get_by_bodega: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener productos: {error_msg}",
            }

    @staticmethod
    def get_one(producto_id: str):
        """
        Trae un solo producto por su ID.

        Parámetros:
            producto_id: el id del producto que queremos buscar
        """
        print(f"--- Buscando producto con id: {producto_id} ---")
        try:
            res = (
                supabase.table("productos")
                .select("*, bodegas(nombre)")
                .eq("id", producto_id)
                .maybe_single()
                .execute()
            )

            if not res.data:
                return {"success": False, "message": "Producto no encontrado"}

            print(f" Producto encontrado: {res.data['nombre']}")
            return {"success": True, "message": "Producto encontrado", "data": res.data}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ProductosService.get_one: {error_msg}")
            return {
                "success": False,
                "message": f"Error al buscar producto: {error_msg}",
            }

    @staticmethod
    def create(
        nombre: str,
        tipo: str,
        funcion: str,
        unidad_medida: str,
        stock: int,
        bodega_id: str,
    ):
        """
        Crea un nuevo producto.

        Parámetros:
            nombre:        nombre del producto, ej: "Perfume Floral 100ml"
            tipo:          categoría, ej: "Perfume", "Envase", "Insumo"
            funcion:       para qué sirve, ej: "Venta directa", "Empaque"
            unidad_medida: solo "gr" (gramos) o "u" (unidades)
            stock:         cantidad inicial disponible
            bodega_id:     id de la bodega donde se almacena
        """
        print(f"--- Creando producto: {nombre} ---")

        if unidad_medida not in UNIDADES_VALIDAS:
            return {
                "success": False,
                "message": f"Unidad de medida inválida. Usa: {UNIDADES_VALIDAS}",
            }

        try:
            nuevo_producto = {
                "nombre": nombre,
                "tipo": tipo,
                "funcion": funcion,
                "unidad_medida": unidad_medida,
                "stock": stock,
                "bodega_id": bodega_id,
            }

            res = supabase.table("productos").insert(nuevo_producto).execute()

            if not res.data:
                return {"success": False, "message": "No se pudo crear el producto"}

            print(f" Producto '{nombre}' creado con éxito")
            return {
                "success": True,
                "message": f"Producto '{nombre}' creado con éxito",
                "data": res.data[0],
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ProductosService.create: {error_msg}")
            return {
                "success": False,
                "message": f"Error al crear producto: {error_msg}",
            }

    @staticmethod
    def update(
        producto_id: str,
        nombre: str,
        tipo: str,
        funcion: str,
        unidad_medida: str,
        bodega_id: str,
    ):
        """
        Actualiza los datos de un producto existente.
        No actualiza el stock aquí — el stock solo cambia a través de movimientos.

        Parámetros:
            producto_id:   el id del producto a actualizar
            nombre:        nuevo nombre
            tipo:          nuevo tipo/categoría
            funcion:       nueva función
            unidad_medida: nueva unidad ("gr" o "u")
            bodega_id:     nueva bodega asignada
        """
        print(f"--- Actualizando producto id: {producto_id} ---")

        if unidad_medida not in UNIDADES_VALIDAS:
            return {
                "success": False,
                "message": f"Unidad de medida inválida. Usa: {UNIDADES_VALIDAS}",
            }

        try:
            datos_actualizados = {
                "nombre": nombre,
                "tipo": tipo,
                "funcion": funcion,
                "unidad_medida": unidad_medida,
                "bodega_id": bodega_id,
            }

            res = (
                supabase.table("productos")
                .update(datos_actualizados)
                .eq("id", producto_id)
                .execute()
            )

            if not res.data:
                return {
                    "success": False,
                    "message": "Producto no encontrado para actualizar",
                }

            print(f" Producto actualizado con éxito")
            return {
                "success": True,
                "message": "Producto actualizado con éxito",
                "data": res.data[0],
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ProductosService.update: {error_msg}")
            return {
                "success": False,
                "message": f"Error al actualizar producto: {error_msg}",
            }

    @staticmethod
    def delete(producto_id: str):
        """
        Elimina un producto por su ID.

        Parámetros:
            producto_id: el id del producto a eliminar
        """
        print(f"--- Eliminando producto id: {producto_id} ---")
        try:
            res = supabase.table("productos").delete().eq("id", producto_id).execute()

            if not res.data:
                return {
                    "success": False,
                    "message": "Producto no encontrado para eliminar",
                }

            print(f" Producto eliminado con éxito")
            return {"success": True, "message": "Producto eliminado con éxito"}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ProductosService.delete: {error_msg}")
            return {
                "success": False,
                "message": f"Error al eliminar producto: {error_msg}",
            }
