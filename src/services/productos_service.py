"""
Servicio de Productos — versión BASE DE DATOS LOCAL.

Ajustado a las columnas REALES de la tabla 'productos' tal como
quedó creada en pgAdmin (distintas al diseño original en Supabase):

    productos (id, bodega_id, nombre, descripcion, sku, precio,
               stock_actual, creado_en)

Mismo contrato de siempre:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - Si hay datos, los incluye bajo la llave 'data'
  - SIN importaciones de Flet — solo lógica pura

⚠️ productos_view.py sigue siendo un stub — cuando la construyan,
   usen estos nombres de parámetro/columna (no 'tipo', 'funcion',
   'unidad_medida' ni 'stock', que no existen en esta tabla).
"""

from src.core.local_db import run_query


class ProductosService:

    @staticmethod
    def get_all():
        """
        Trae todos los productos.
        Incluye el nombre de la bodega a la que pertenece cada uno.
        """
        print("--- Trayendo todos los productos ---")
        try:
            data = run_query("""
                SELECT p.*, b.nombre AS bodega_nombre
                FROM productos p
                LEFT JOIN bodegas b ON p.bodega_id = b.id
                ORDER BY p.nombre
                """)

            if not data:
                print("⚠️ No hay productos registrados aún")
                return {"success": False, "message": "No hay productos registrados"}

            print(f"✅ Se encontraron {len(data)} producto(s)")
            return {"success": True, "message": "Productos obtenidos", "data": data}

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
            data = run_query(
                "SELECT * FROM productos WHERE bodega_id = %s ORDER BY nombre",
                (bodega_id,),
            )

            if not data:
                return {"success": False, "message": "No hay productos en esta bodega"}

            print(f"✅ Se encontraron {len(data)} producto(s) en la bodega")
            return {"success": True, "message": "Productos obtenidos", "data": data}

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
            producto = run_query(
                """
                SELECT p.*, b.nombre AS bodega_nombre
                FROM productos p
                LEFT JOIN bodegas b ON p.bodega_id = b.id
                WHERE p.id = %s
                """,
                (producto_id,),
                fetch_one=True,
            )

            if not producto:
                return {"success": False, "message": "Producto no encontrado"}

            print(f"✅ Producto encontrado: {producto['nombre']}")
            return {"success": True, "message": "Producto encontrado", "data": producto}

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
        descripcion: str,
        sku: str,
        precio: float,
        stock_actual: int,
        bodega_id: str,
    ):
        """
        Crea un nuevo producto.

        Parámetros:
            nombre:       nombre del producto, ej: "Perfume Floral 100ml"
            descripcion:  detalle libre del producto
            sku:          código interno/referencia del producto
            precio:       precio de venta
            stock_actual: cantidad inicial disponible
            bodega_id:    id de la bodega donde se almacena
        """
        print(f"--- Creando producto: {nombre} ---")
        try:
            producto = run_query(
                """
                INSERT INTO productos
                    (nombre, descripcion, sku, precio, stock_actual, bodega_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (nombre, descripcion, sku, precio, stock_actual, bodega_id),
                fetch_one=True,
            )

            if not producto:
                return {"success": False, "message": "No se pudo crear el producto"}

            print(f" Producto '{nombre}' creado con éxito")
            return {
                "success": True,
                "message": f"Producto '{nombre}' creado con éxito",
                "data": producto,
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
        descripcion: str,
        sku: str,
        precio: float,
        bodega_id: str,
    ):
        """
        Actualiza los datos de un producto existente.
        No actualiza stock_actual aquí — el stock solo cambia a través
        de movimientos (ver movimientos_service.py).

        Parámetros:
            producto_id: el id del producto a actualizar
            nombre:      nuevo nombre
            descripcion: nueva descripción
            sku:         nuevo código/referencia
            precio:      nuevo precio
            bodega_id:   nueva bodega asignada
        """
        print(f"--- Actualizando producto id: {producto_id} ---")
        try:
            producto = run_query(
                """
                UPDATE productos
                SET nombre = %s,
                    descripcion = %s,
                    sku = %s,
                    precio = %s,
                    bodega_id = %s
                WHERE id = %s
                RETURNING *
                """,
                (nombre, descripcion, sku, precio, bodega_id, producto_id),
                fetch_one=True,
            )

            if not producto:
                return {
                    "success": False,
                    "message": "Producto no encontrado para actualizar",
                }

            print(f" Producto actualizado con éxito")
            return {
                "success": True,
                "message": "Producto actualizado con éxito",
                "data": producto,
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
            eliminado = run_query(
                "DELETE FROM productos WHERE id = %s RETURNING id",
                (producto_id,),
                fetch_one=True,
            )

            if not eliminado:
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
