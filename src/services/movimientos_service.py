"""
Servicio de Movimientos de Inventario — versión BASE DE DATOS LOCAL.

Registra toda entrada, salida, ajuste o baja de productos en las bodegas.
Cada operación hace DOS cosas dentro de la MISMA transacción (usando
get_cursor() de local_db, con bloqueo de fila para evitar condiciones
de carrera si dos ventas tocan el mismo producto a la vez):
  1. Inserta un registro en 'movimientos' (historial/trazabilidad)
  2. Actualiza 'stock_actual' del producto correspondiente

⚠️ Sobre 'tipo':
    La tabla 'movimientos' en Postgres (ver Rey_base_de_datos.sql) solo
    permite los valores 'ingreso', 'egreso' y 'transferencia':

        CONSTRAINT movimientos_tipo_check CHECK (tipo IN
            ('ingreso', 'egreso', 'transferencia'))

    Como la interfaz maneja Entrada / Salida / Baja / Ajuste, este
    servicio traduce internamente:
        entrada -> "ingreso"
        salida  -> "egreso"
        baja    -> "egreso"  (con el motivo prefijado "BAJA: ...")
        ajuste  -> "egreso"  (con el motivo prefijado "AJUSTE: ...")

    Si más adelante quieren una categoría 'baja' separada de verdad en
    la base de datos, hay que ampliar esa restricción, por ejemplo:

        ALTER TABLE movimientos DROP CONSTRAINT movimientos_tipo_check;
        ALTER TABLE movimientos ADD CONSTRAINT movimientos_tipo_check
            CHECK (tipo IN ('ingreso', 'egreso', 'transferencia', 'baja'));

Mismo contrato que los demás servicios locales:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - SIN importaciones de Flet — solo lógica pura
"""

from src.core.local_db import get_cursor, run_query
from src.services.bitacora_service import BitacoraService

TIPOS_VALIDOS = ["entrada", "salida", "baja", "ajuste"]

# Cómo se traduce cada tipo de la UI al valor que acepta la base de datos.
_TIPO_DB = {
    "entrada": "ingreso",
    "salida": "egreso",
    "baja": "egreso",
    "ajuste": "egreso",
}


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
                SELECT m.*,
                       p.nombre AS producto_nombre,
                       b.nombre AS bodega_nombre,
                       u.name  AS usuario_nombre
                FROM movimientos m
                LEFT JOIN productos p ON m.producto_id = p.id
                LEFT JOIN bodegas b ON m.bodega_id = b.id
                LEFT JOIN usuarios u ON m.usuario_id = u.id
                ORDER BY m.fecha DESC
                """)

            if not data:
                return {"success": False, "message": "No hay movimientos registrados"}

            print(f"✅ Se encontraron {len(data)} movimiento(s)")
            return {"success": True, "message": "Movimientos obtenidos", "data": data}

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
                    "success": False,
                    "message": "No hay movimientos para este producto",
                }

            return {"success": True, "message": "Movimientos obtenidos", "data": data}

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
        tipo_ui: str,
        cantidad: int,
        motivo: str,
        usuario_id: str,
    ):
        """
        Función interna que hace el trabajo real, dentro de una sola
        transacción (SELECT ... FOR UPDATE + INSERT + UPDATE), para que
        el movimiento y el nuevo stock queden siempre sincronizados.
        """
        if tipo_ui not in _TIPO_DB:
            return {
                "success": False,
                "message": f"Tipo de movimiento inválido: {tipo_ui}",
            }

        if cantidad <= 0:
            return {"success": False, "message": "La cantidad debe ser mayor a 0"}

        tipo_db = _TIPO_DB[tipo_ui]

        try:
            with get_cursor() as cur:
                cur.execute(
                    "SELECT nombre, stock_actual FROM productos WHERE id = %s FOR UPDATE",
                    (producto_id,),
                )
                producto = cur.fetchone()

                if not producto:
                    return {"success": False, "message": "Producto no encontrado"}

                stock_actual = producto["stock_actual"]
                nombre_producto = producto["nombre"]

                if tipo_db == "ingreso":
                    nuevo_stock = stock_actual + cantidad
                else:
                    if stock_actual < cantidad:
                        return {
                            "success": False,
                            "message": (
                                f"Stock insuficiente. Disponible: {stock_actual}, "
                                f"solicitado: {cantidad}"
                            ),
                        }
                    nuevo_stock = stock_actual - cantidad

                cur.execute(
                    """
                    INSERT INTO movimientos
                        (producto_id, bodega_id, usuario_id, tipo, cantidad, motivo)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (producto_id, bodega_id, usuario_id, tipo_db, cantidad, motivo),
                )
                movimiento = cur.fetchone()

                cur.execute(
                    "UPDATE productos SET stock_actual = %s WHERE id = %s",
                    (nuevo_stock, producto_id),
                )

            print(
                f"✅ Movimiento registrado: {tipo_ui} de {cantidad} unidades de "
                f"'{nombre_producto}'"
            )
            print(f"   Stock anterior: {stock_actual} → Stock nuevo: {nuevo_stock}")

            MovimientosService._registrar_bitacora(
                usuario_id,
                tipo_ui,
                cantidad,
                nombre_producto,
                motivo,
            )

            return {
                "success": True,
                "message": f"Movimiento registrado. Stock actualizado a {nuevo_stock}",
                "data": movimiento,
            }

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en MovimientosService._registrar_movimiento: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar movimiento: {error_msg}",
            }

    @staticmethod
    def registrar_entrada(
        producto_id: str, bodega_id: str, cantidad: int, motivo: str, usuario_id: str
    ):
        """Registra la ENTRADA de productos a una bodega (aumenta el stock)."""
        return MovimientosService._registrar_movimiento(
            producto_id, bodega_id, "entrada", cantidad, motivo, usuario_id
        )

    @staticmethod
    def registrar_salida(
        producto_id: str, bodega_id: str, cantidad: int, motivo: str, usuario_id: str
    ):
        """Registra la SALIDA de productos de una bodega (reduce el stock)."""
        return MovimientosService._registrar_movimiento(
            producto_id, bodega_id, "salida", cantidad, motivo, usuario_id
        )

    @staticmethod
    def registrar_ajuste(
        producto_id: str, bodega_id: str, cantidad: int, motivo: str, usuario_id: str
    ):
        """Registra un AJUSTE MANUAL por faltantes o sobrantes (reduce el stock)."""
        motivo_final = f"AJUSTE: {motivo}" if motivo else "AJUSTE"
        return MovimientosService._registrar_movimiento(
            producto_id, bodega_id, "ajuste", cantidad, motivo_final, usuario_id
        )

    @staticmethod
    def registrar_baja(
        producto_id: str, bodega_id: str, cantidad: int, motivo: str, usuario_id: str
    ):
        """Registra una BAJA por productos dañados o caducados (reduce el stock)."""
        motivo_final = f"BAJA: {motivo}" if motivo else "BAJA"
        return MovimientosService._registrar_movimiento(
            producto_id, bodega_id, "baja", cantidad, motivo_final, usuario_id
        )

    # ─────────────────────────────────────────────────────────────────
    # Bitácora
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _registrar_bitacora(usuario_id, tipo_ui, cantidad, nombre_producto, motivo):
        """Deja constancia del movimiento en la bitácora (best-effort)."""
        descripcion = (
            f"{tipo_ui.capitalize()} de {cantidad} unidad(es) de '{nombre_producto}'"
        )
        if motivo:
            descripcion += f" — {motivo}"

        resultado = BitacoraService.registrar_evento(
            usuario_id, "MOVIMIENTO", descripcion
        )
        if not resultado["success"]:
            print(f"⚠️ No se pudo registrar en bitácora: {resultado['message']}")
