"""
Servicio de Movimientos de Inventario.

Registra TODA entrada, salida, ajuste o baja de productos en las bodegas.
Este servicio hace DOS cosas al mismo tiempo en cada operación:
  1. Inserta un registro en la tabla 'movimientos' (historial/trazabilidad)
  2. Actualiza el stock del producto en la tabla 'productos'

Sigue el mismo patrón que auth_service.py:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - SIN importaciones de Flet — solo lógica pura

Tabla esperada en Supabase:
    movimientos (id, producto_id, bodega_id, tipo, cantidad, motivo, fecha, usuario_id)

    tipo solo puede ser: "entrada", "salida", "ajuste", "baja"
"""

from src.core.supabase_client import supabase

TIPOS_VALIDOS = ["entrada", "salida", "ajuste", "baja"]


class MovimientosService:

    @staticmethod
    def get_all():
        """
        Trae el historial completo de todos los movimientos.
        Incluye el nombre del producto y la bodega relacionados.
        """
        print("--- Trayendo todos los movimientos ---")
        try:
            res = (
                supabase.table("movimientos")
                .select("*, productos(nombre), bodegas(nombre)")
                .order("fecha", desc=True)
                .execute()
            )

            if not res.data:
                return {"success": False, "message": "No hay movimientos registrados"}

            print(f"✅ Se encontraron {len(res.data)} movimiento(s)")
            return {
                "success": True,
                "message": "Movimientos obtenidos",
                "data": res.data,
            }

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en MovimientosService.get_all: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener movimientos: {error_msg}",
            }

    @staticmethod
    def get_by_producto(producto_id: str):
        """
        Trae todos los movimientos de un producto específico.
        Útil para ver el historial de un producto en particular.
        """
        print(f"--- Trayendo movimientos del producto: {producto_id} ---")
        try:
            res = (
                supabase.table("movimientos")
                .select("*")
                .eq("producto_id", producto_id)
                .order("fecha", desc=True)
                .execute()
            )

            if not res.data:
                return {
                    "success": False,
                    "message": "No hay movimientos para este producto",
                }

            return {
                "success": True,
                "message": "Movimientos obtenidos",
                "data": res.data,
            }

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en MovimientosService.get_by_producto: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener movimientos: {error_msg}",
            }

    @staticmethod
    def _registrar_movimiento(
        producto_id: str,
        bodega_id: str,
        tipo: str,
        cantidad: int,
        motivo: str,
        usuario_id: str,
    ):
        """
        Función interna (privada) que hace el trabajo real.
        El guión bajo al inicio (_) es la convención en Python para decir
        "este método es solo para uso interno de esta clase".

        Hace dos pasos:
          Paso 1: Verifica que el producto existe y tiene stock suficiente
          Paso 2: Inserta el movimiento Y actualiza el stock al mismo tiempo
        """

        producto_res = (
            supabase.table("productos")
            .select("id, nombre, stock")
            .eq("id", producto_id)
            .maybe_single()
            .execute()
        )

        if not producto_res.data:
            return {"success": False, "message": "Producto no encontrado"}

        stock_actual = producto_res.data["stock"]
        nombre_producto = producto_res.data["nombre"]

        if tipo == "entrada":
            nuevo_stock = stock_actual + cantidad
        else:
            if stock_actual < cantidad:
                return {
                    "success": False,
                    "message": f"Stock insuficiente. Disponible: {stock_actual}, solicitado: {cantidad}",
                }
            nuevo_stock = stock_actual - cantidad

        nuevo_movimiento = {
            "producto_id": producto_id,
            "bodega_id": bodega_id,
            "tipo": tipo,
            "cantidad": cantidad,
            "motivo": motivo,
            "usuario_id": usuario_id,
        }

        mov_res = supabase.table("movimientos").insert(nuevo_movimiento).execute()

        if not mov_res.data:
            return {"success": False, "message": "No se pudo registrar el movimiento"}

        supabase.table("productos").update({"stock": nuevo_stock}).eq(
            "id", producto_id
        ).execute()

        print(
            f"✅ Movimiento registrado: {tipo} de {cantidad} unidades de '{nombre_producto}'"
        )
        print(f"   Stock anterior: {stock_actual} → Stock nuevo: {nuevo_stock}")

        return {
            "success": True,
            "message": f"Movimiento registrado. Stock actualizado a {nuevo_stock}",
            "data": mov_res.data[0],
        }

    @staticmethod
    def registrar_entrada(
        producto_id: str, bodega_id: str, cantidad: int, motivo: str, usuario_id: str
    ):
        """
        Registra la ENTRADA de productos a una bodega (aumenta el stock).
        Ej: llegó una compra nueva de 50 unidades de perfume.

        Parámetros:
            producto_id: id del producto que entra
            bodega_id:   id de la bodega que recibe
            cantidad:    cuántas unidades entran
            motivo:      razón de la entrada, ej: "Compra proveedor X"
            usuario_id:  id del usuario que registra la acción
        """
        print(f"--- Registrando ENTRADA de {cantidad} unidades ---")
        try:
            return MovimientosService._registrar_movimiento(
                producto_id, bodega_id, "entrada", cantidad, motivo, usuario_id
            )
        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en registrar_entrada: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar entrada: {error_msg}",
            }

    @staticmethod
    def registrar_salida(
        producto_id: str, bodega_id: str, cantidad: int, motivo: str, usuario_id: str
    ):
        """
        Registra la SALIDA de productos de una bodega (reduce el stock).
        Ej: se retiraron 10 unidades para un evento.

        Parámetros:
            producto_id: id del producto que sale
            bodega_id:   id de la bodega de origen
            cantidad:    cuántas unidades salen
            motivo:      razón de la salida, ej: "Retiro para evento"
            usuario_id:  id del usuario que registra la acción
        """
        print(f"--- Registrando SALIDA de {cantidad} unidades ---")
        try:
            return MovimientosService._registrar_movimiento(
                producto_id, bodega_id, "salida", cantidad, motivo, usuario_id
            )
        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en registrar_salida: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar salida: {error_msg}",
            }

    @staticmethod
    def registrar_ajuste(
        producto_id: str, bodega_id: str, cantidad: int, motivo: str, usuario_id: str
    ):
        """
        Registra un AJUSTE MANUAL por faltantes o sobrantes (reduce el stock).
        Ej: al hacer inventario físico se encontraron 5 unidades menos.

        Parámetros:
            producto_id: id del producto a ajustar
            bodega_id:   id de la bodega
            cantidad:    cuántas unidades se ajustan (siempre positivo)
            motivo:      razón del ajuste, ej: "Faltante en conteo físico"
            usuario_id:  id del usuario que registra la acción
        """
        print(f"--- Registrando AJUSTE de {cantidad} unidades ---")
        try:
            return MovimientosService._registrar_movimiento(
                producto_id, bodega_id, "ajuste", cantidad, motivo, usuario_id
            )
        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en registrar_ajuste: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar ajuste: {error_msg}",
            }

    @staticmethod
    def registrar_baja(
        producto_id: str, bodega_id: str, cantidad: int, motivo: str, usuario_id: str
    ):
        """
        Registra una BAJA por productos dañados o caducados (reduce el stock).
        Ej: 3 frascos de perfume se rompieron durante el almacenamiento.

        Parámetros:
            producto_id: id del producto dado de baja
            bodega_id:   id de la bodega
            cantidad:    cuántas unidades se dan de baja
            motivo:      razón: "Daño físico", "Producto caducado", etc.
            usuario_id:  id del usuario que registra la acción
        """
        print(f"--- Registrando BAJA de {cantidad} unidades ---")
        try:
            return MovimientosService._registrar_movimiento(
                producto_id, bodega_id, "baja", cantidad, motivo, usuario_id
            )
        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en registrar_baja: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar baja: {error_msg}",
            }
