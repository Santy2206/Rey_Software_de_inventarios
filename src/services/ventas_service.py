"""
Servicio de Ventas — base de datos local.

Registra una venta con sus líneas, descuenta el stock de cada producto
y deja un movimiento de tipo 'egreso' para trazabilidad. Todo ocurre
en UNA sola transacción (get_cursor + SELECT ... FOR UPDATE) para que
dos ventas simultáneas no vendan el mismo stock.

Tablas:
    ventas         (id, cliente_id, usuario_id, total, fecha)
    venta_detalle  (id, venta_id, producto_id, cantidad, precio_unitario, subtotal)

Mismo contrato que el resto de servicios:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - SIN importaciones de Flet — solo lógica pura
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from src.core.local_db import get_cursor, run_query
from src.services.bitacora_service import BitacoraService


class _VentaError(Exception):
    """Error de negocio: hace rollback de la transacción al salir del with."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _qty(value) -> Decimal:
    """Cantidad con hasta 4 decimales (gramos de esencia / combos)."""
    return Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _as_id(value) -> str | None:
    return str(value) if value is not None else None


class VentasService:

    @staticmethod
    def get_all():
        """
        Trae el historial de ventas con cliente, usuario y totales de líneas.
        """
        print("--- Trayendo todas las ventas ---")
        try:
            data = run_query(
                """
                SELECT v.id,
                       v.cliente_id,
                       v.usuario_id,
                       v.total,
                       v.fecha,
                       v.anulada,
                       c.nombre AS cliente_nombre,
                       u.name   AS usuario_nombre,
                       COUNT(d.id) AS items,
                       COALESCE(SUM(d.cantidad), 0) AS unidades
                FROM ventas v
                LEFT JOIN clientes c ON v.cliente_id = c.id
                LEFT JOIN usuarios u ON v.usuario_id = u.id
                LEFT JOIN venta_detalle d ON d.venta_id = v.id
                GROUP BY v.id, c.nombre, u.name
                ORDER BY v.fecha DESC
                """
            )

            if not data:
                return {"success": False, "message": "No hay ventas registradas"}

            print(f" Se encontraron {len(data)} venta(s)")
            return {"success": True, "message": "Ventas obtenidas", "data": data}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en VentasService.get_all: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener ventas: {error_msg}",
            }

    @staticmethod
    def total_hoy():
        """Suma el total de las ventas del día actual (fecha local del servidor)."""
        print("--- Calculando total de ventas de hoy ---")
        try:
            fila = run_query(
                """
                SELECT COALESCE(SUM(total), 0) AS total
                FROM ventas
                WHERE fecha::date = CURRENT_DATE
                  AND COALESCE(anulada, false) = false
                """,
                fetch_one=True,
            )
            total = _money(fila["total"] if fila else 0)
            return {"success": True, "message": "Total de hoy", "data": total}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en VentasService.total_hoy: {error_msg}")
            return {
                "success": False,
                "message": f"Error al calcular ventas de hoy: {error_msg}",
                "data": Decimal("0.00"),
            }

    @staticmethod
    def registrar(
        cliente_id: str,
        items: list[dict],
        usuario_id: str = None,
        fecha=None,
        total_forzado=None,
        permitir_stock_negativo: bool = False,
        motivo_movimiento: str | None = None,
    ):
        """
        Registra una venta.

        Parámetros:
            cliente_id: id del cliente que compra
            items:      lista de {
                            producto_id,
                            cantidad,              # int o decimal
                            precio_unitario?,      # opcional override
                            subtotal?,             # opcional override
                        }
            usuario_id: id del usuario que registra
            fecha:      datetime o str ISO opcional (import Elisa)
            total_forzado: si se indica, el total de la venta se fija a este
                           valor (p.ej. CREDITO del archivo Elisa), aunque
                           el reparto de líneas use precios internos.
            permitir_stock_negativo: si True, no bloquea por stock insuficiente
                           (útil al importar histórico con stock aún no
                           cargado; el movimiento y el stock se actualizan
                           igual). Por defecto False (RF07/RF08 manual).
            motivo_movimiento: texto del movimiento; default 'VENTA {id}'.

        Efectos en la misma transacción:
            1. INSERT en ventas
            2. INSERT en venta_detalle
            3. UPDATE productos.stock_actual (bloqueo de fila)
            4. INSERT en movimientos tipo 'egreso'
        """
        print("--- Registrando venta ---")
        try:
            if not cliente_id:
                return {"success": False, "message": "El cliente es obligatorio"}

            lineas = VentasService._normalizar_items(items)
            if not lineas:
                return {
                    "success": False,
                    "message": "Agrega al menos un producto a la venta",
                }

            with get_cursor() as cur:
                usuario_local = VentasService._resolver_usuario_id(cur, usuario_id)
                if not usuario_local:
                    raise _VentaError(
                        "No hay un usuario local válido para registrar la venta"
                    )

                cur.execute(
                    "SELECT id, nombre FROM clientes WHERE id = %s",
                    (cliente_id,),
                )
                cliente = cur.fetchone()
                if not cliente:
                    raise _VentaError("Cliente no encontrado")

                if fecha is None:
                    cur.execute(
                        """
                        INSERT INTO ventas (cliente_id, usuario_id, total)
                        VALUES (%s, %s, %s)
                        RETURNING *
                        """,
                        (cliente_id, usuario_local, Decimal("0.00")),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO ventas (cliente_id, usuario_id, total, fecha)
                        VALUES (%s, %s, %s, %s)
                        RETURNING *
                        """,
                        (cliente_id, usuario_local, Decimal("0.00"), fecha),
                    )
                venta = cur.fetchone()
                venta_id = venta["id"]

                total = Decimal("0.00")
                motivo = motivo_movimiento or f"VENTA {venta_id}"

                for linea in lineas:
                    producto_id = linea["producto_id"]
                    cantidad = _qty(linea["cantidad"])
                    if cantidad <= 0:
                        raise _VentaError("La cantidad debe ser mayor a 0")

                    cur.execute(
                        """
                        SELECT id, nombre, precio, stock_actual, bodega_id
                        FROM productos
                        WHERE id = %s
                        FOR UPDATE
                        """,
                        (producto_id,),
                    )
                    producto = cur.fetchone()
                    if not producto:
                        raise _VentaError(f"Producto no encontrado: {producto_id}")

                    stock_actual = _qty(producto["stock_actual"] or 0)
                    if (not permitir_stock_negativo) and stock_actual < cantidad:
                        raise _VentaError(
                            f"Stock insuficiente de '{producto['nombre']}'. "
                            f"Disponible: {stock_actual}, solicitado: {cantidad}"
                        )

                    if "precio_unitario" in linea and linea["precio_unitario"] is not None:
                        precio = _money(linea["precio_unitario"])
                    else:
                        precio = _money(producto["precio"])

                    if "subtotal" in linea and linea["subtotal"] is not None:
                        subtotal = _money(linea["subtotal"])
                    else:
                        subtotal = _money(precio * cantidad)

                    total += subtotal
                    nuevo_stock = stock_actual - cantidad

                    cur.execute(
                        """
                        INSERT INTO venta_detalle
                            (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (venta_id, producto_id, cantidad, precio, subtotal),
                    )
                    cur.execute(
                        """
                        UPDATE productos
                        SET stock_actual = %s, dirty = true
                        WHERE id = %s
                        """,
                        (nuevo_stock, producto_id),
                    )
                    cur.execute(
                        """
                        INSERT INTO movimientos
                            (producto_id, bodega_id, usuario_id, tipo, cantidad, motivo)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            producto_id,
                            producto["bodega_id"],
                            usuario_local,
                            "egreso",
                            cantidad,
                            motivo,
                        ),
                    )

                if total_forzado is not None:
                    total = _money(total_forzado)

                cur.execute(
                    "UPDATE ventas SET total = %s, dirty = true WHERE id = %s RETURNING *",
                    (total, venta_id),
                )
                venta = cur.fetchone()

            print(f" Venta {venta_id} registrada. Total: {total}")
            return {
                "success": True,
                "message": f"Venta registrada. Total ${total}",
                "data": venta,
            }

        except _VentaError as e:
            return {"success": False, "message": e.message}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en VentasService.registrar: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar la venta: {error_msg}",
            }

    @staticmethod
    def anular(venta_id: str, usuario_id: str = None):
        """
        Anula una venta: la marca como anulada y devuelve el stock
        de cada producto vendido (movimiento 'ingreso' por línea).

        Parámetros:
            venta_id:   id de la venta a anular
            usuario_id: id del usuario que anula (para bitácora y
                        movimientos; si no coincide con usuarios.id
                        local, se usa el primer usuario de la BD)

        Efectos en la misma transacción:
            1. UPDATE ventas SET anulada = true
            2. UPDATE productos.stock_actual += cantidad por línea
            3. INSERT en movimientos tipo 'ingreso' (motivo ANULACION)
            4. Registro en bitácora (ANULACION_VENTA)
        """
        print(f"--- Anulando venta id: {venta_id} ---")
        try:
            if not venta_id:
                return {"success": False, "message": "La venta es obligatoria"}

            usuario_local = None
            total = Decimal("0.00")

            with get_cursor() as cur:
                usuario_local = VentasService._resolver_usuario_id(
                    cur, usuario_id
                )
                if not usuario_local:
                    raise _VentaError(
                        "No hay un usuario local válido para anular la venta"
                    )

                cur.execute(
                    """
                    SELECT id, total, anulada
                    FROM ventas
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (venta_id,),
                )
                venta = cur.fetchone()
                if not venta:
                    raise _VentaError("Venta no encontrada")
                if venta.get("anulada"):
                    raise _VentaError("La venta ya está anulada")

                total = _money(venta["total"])

                cur.execute(
                    """
                    SELECT d.producto_id,
                           d.cantidad,
                           p.bodega_id,
                           p.nombre AS producto_nombre
                    FROM venta_detalle d
                    JOIN productos p ON p.id = d.producto_id
                    WHERE d.venta_id = %s
                    """,
                    (venta_id,),
                )
                detalles = cur.fetchall() or []

                for det in detalles:
                    cur.execute(
                        """
                        UPDATE productos
                        SET stock_actual = stock_actual + %s
                        WHERE id = %s
                        """,
                        (det["cantidad"], det["producto_id"]),
                    )
                    cur.execute(
                        """
                        INSERT INTO movimientos
                            (producto_id, bodega_id, usuario_id, tipo, cantidad, motivo)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            det["producto_id"],
                            det["bodega_id"],
                            usuario_local,
                            "ingreso",
                            det["cantidad"],
                            f"ANULACION VENTA {venta_id}",
                        ),
                    )

                cur.execute(
                    "UPDATE ventas SET anulada = true, dirty = true WHERE id = %s",
                    (venta_id,),
                )

            BitacoraService.registrar(
                usuario_local,
                "ANULACION_VENTA",
                entidad="venta",
                entidad_id=venta_id,
                detalle=f"Venta anulada. Total devuelto: ${total}",
            )

            print(f" Venta {venta_id} anulada")
            return {"success": True, "message": "Venta anulada con éxito"}

        except _VentaError as e:
            return {"success": False, "message": e.message}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en VentasService.anular: {error_msg}")
            return {
                "success": False,
                "message": f"Error al anular la venta: {error_msg}",
            }

    @staticmethod
    def _normalizar_items(items: list[dict]) -> list[dict]:
        """
        Normaliza líneas de venta.

        Si varias líneas del mismo producto_id no traen precio/subtotal
        custom, se agrupan sumando cantidades. Las que traen overrides
        se conservan como líneas independientes.
        """
        agrupado: dict[str, Decimal] = {}
        extras: list[dict] = []
        for item in items or []:
            producto_id = _as_id(item.get("producto_id"))
            if not producto_id:
                continue
            try:
                cantidad = _qty(item.get("cantidad") or 0)
            except Exception:
                continue
            if cantidad <= 0:
                continue

            tiene_override = (
                item.get("precio_unitario") is not None
                or item.get("subtotal") is not None
            )
            if tiene_override:
                extras.append(
                    {
                        "producto_id": producto_id,
                        "cantidad": cantidad,
                        "precio_unitario": item.get("precio_unitario"),
                        "subtotal": item.get("subtotal"),
                    }
                )
            else:
                agrupado[producto_id] = agrupado.get(producto_id, Decimal("0")) + cantidad

        out = [
            {"producto_id": pid, "cantidad": cant} for pid, cant in agrupado.items()
        ]
        out.extend(extras)
        return out

    @staticmethod
    def _resolver_usuario_id(cur, usuario_id: str | None) -> str | None:
        """
        ventas.usuario_id apunta a usuarios.id de la BD local.
        AuthService.get_usuario_id() puede devolver el UUID de Supabase Auth,
        que no coincide. Si el id no existe en local, se usa el primer usuario.
        """
        if usuario_id:
            cur.execute("SELECT id FROM usuarios WHERE id = %s", (str(usuario_id),))
            fila = cur.fetchone()
            if fila:
                return str(fila["id"])

        cur.execute("SELECT id FROM usuarios ORDER BY creado_en LIMIT 1")
        fila = cur.fetchone()
        return str(fila["id"]) if fila else None
