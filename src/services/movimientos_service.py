"""
Servicio de Movimientos de Inventario.

Registra TODA entrada, salida, ajuste o baja de productos en las bodegas.
Este servicio hace DOS cosas atómicas en cada operación:
  1. Inserta un registro en la tabla 'movimientos' (historial/trazabilidad)
  2. Actualiza el stock del producto en la tabla 'productos'

Sigue el mismo patrón que el resto de servicios:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - SIN importaciones de Flet — solo lógica pura

Tabla local:
    movimientos (id, producto_id, bodega_id, usuario_id, tipo, cantidad, fecha, motivo)

    tipo solo puede ser: "ingreso", "egreso", "transferencia"
    (según el CHECK CONSTRAINT movimientos_tipo_check de PostgreSQL)
"""

from src.core.local_db import get_cursor, run_query
from src.services.bitacora_service import BitacoraService

TIPOS_VALIDOS = ["ingreso", "egreso", "transferencia"]


class MovimientosService:

    @staticmethod
    def get_all():
        """
        Trae el historial completo de todos los movimientos.
        Incluye el nombre del producto, la bodega y el usuario relacionados.
        """
        print("--- Trayendo todos los movimientos ---")
        try:
            data = run_query("""
                SELECT
                    m.*,
                    p.nombre AS producto_nombre,
                    b.nombre AS bodega_nombre,
                    u.name AS usuario_name
                FROM movimientos m
                LEFT JOIN productos p ON m.producto_id = p.id
                LEFT JOIN bodegas b ON m.bodega_id = b.id
                LEFT JOIN usuarios u ON m.usuario_id = u.id
                ORDER BY m.fecha DESC
            """)

            if not data:
                print("⚠️ No hay movimientos registrados aún")
                return {
                    "success": True,
                    "message": "No hay movimientos registrados",
                    "data": [],
                }

            print(f"✅ Se encontraron {len(data)} movimiento(s)")
            return {
                "success": True,
                "message": "Movimientos obtenidos",
                "data": data,
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
            data = run_query(
                "SELECT * FROM movimientos WHERE producto_id = %s ORDER BY fecha DESC",
                (producto_id,),
            )

            if not data:
                return {
                    "success": True,
                    "message": "No hay movimientos para este producto",
                    "data": [],
                }

            return {
                "success": True,
                "message": "Movimientos obtenidos",
                "data": data,
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

        Hace dos pasos atómicos dentro de una transacción:
          Paso 1: Verifica que el producto existe y tiene stock suficiente
          Paso 2: Inserta el movimiento Y actualiza el stock al mismo tiempo
        """
        if tipo not in TIPOS_VALIDOS:
            return {
                "success": False,
                "message": f"Tipo de movimiento no válido: {tipo}",
            }

        with get_cursor() as cur:
            cur.execute(
                "SELECT id, nombre, stock_actual FROM productos WHERE id = %s FOR UPDATE",
                (producto_id,),
            )
            producto = cur.fetchone()

            if not producto:
                return {"success": False, "message": "Producto no encontrado"}

            stock_actual = producto["stock_actual"]
            nombre_producto = producto["nombre"]

            if tipo == "ingreso":
                nuevo_stock = stock_actual + cantidad
            else:
                if stock_actual < cantidad:
                    return {
                        "success": False,
                        "message": f"Stock insuficiente. Disponible: {stock_actual}, solicitado: {cantidad}",
                    }
                nuevo_stock = stock_actual - cantidad

            cur.execute(
                """
                INSERT INTO movimientos
                    (producto_id, bodega_id, usuario_id, tipo, cantidad, motivo, fecha)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING *
                """,
                (producto_id, bodega_id, usuario_id, tipo, cantidad, motivo),
            )
            movimiento = cur.fetchone()

            cur.execute(
                "UPDATE productos SET stock_actual = %s WHERE id = %s",
                (nuevo_stock, producto_id),
            )

        print(
            f"✅ Movimiento registrado: {tipo} de {cantidad} unidades de '{nombre_producto}'"
        )
        print(f"   Stock anterior: {stock_actual} → Stock nuevo: {nuevo_stock}")

        BitacoraService.registrar(
            usuario_id,
            "MOVIMIENTO",
            {
                "descripcion": f"Movimiento {tipo} de {cantidad} unidades de '{nombre_producto}'",
                "producto_id": producto_id,
                "bodega_id": bodega_id,
                "tipo": tipo,
                "cantidad": cantidad,
                "motivo": motivo,
                "stock_anterior": stock_actual,
                "stock_nuevo": nuevo_stock,
            },
        )

        return {
            "success": True,
            "message": f"Movimiento registrado. Stock actualizado a {nuevo_stock}",
            "data": movimiento,
        }

    @staticmethod
    def registrar_entrada(
        producto_id: str, bodega_id: str, cantidad: int, motivo: str, usuario_id: str
    ):
        """
        Registra la ENTRADA de productos a una bodega (aumenta el stock).
        Ej: llegó una compra nueva de 50 unidades de perfume.
        En la base de datos el tipo del movimiento es "ingreso".

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
                producto_id, bodega_id, "ingreso", cantidad, motivo, usuario_id
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
        En la base de datos el tipo del movimiento es "egreso".

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
                producto_id, bodega_id, "egreso", cantidad, motivo, usuario_id
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
        En la base de datos el tipo del movimiento es "egreso".

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
                producto_id, bodega_id, "egreso", cantidad, motivo, usuario_id
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
        En la base de datos el tipo del movimiento es "egreso".

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
                producto_id, bodega_id, "egreso", cantidad, motivo, usuario_id
            )
        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en registrar_baja: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar baja: {error_msg}",
            }
