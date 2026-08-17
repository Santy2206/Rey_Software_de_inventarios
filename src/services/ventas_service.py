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

from decimal import Decimal, ROUND_HALF_UP

from psycopg2.extras import Json

from src.core.local_db import get_cursor, run_query


class _VentaError(Exception):
    """Error de negocio: hace rollback de la transacción al salir del with."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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
    def registrar(cliente_id: str, items: list[dict], usuario_id: str = None):
        """
        Registra una venta.

        Parámetros:
            cliente_id: id del cliente que compra
            items:      lista de {producto_id, cantidad}
            usuario_id: id del usuario que registra (si no coincide con
                        usuarios.id local, se usa el primer usuario de la BD)

        Efectos en la misma transacción:
            1. INSERT en ventas
            2. INSERT en venta_detalle (precio tomado de productos.precio)
            3. UPDATE productos.stock_actual (con bloqueo de fila)
            4. INSERT en movimientos tipo 'egreso' (motivo VENTA)
            5. INSERT en bitácora (best-effort dentro de la misma transacción)
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

                cur.execute(
                    """
                    INSERT INTO ventas (cliente_id, usuario_id, total)
                    VALUES (%s, %s, %s)
                    RETURNING *
                    """,
                    (cliente_id, usuario_local, Decimal("0.00")),
                )
                venta = cur.fetchone()
                venta_id = venta["id"]

                total = Decimal("0.00")
                nombres = []

                for linea in lineas:
                    producto_id = linea["producto_id"]
                    cantidad = linea["cantidad"]

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

                    stock_actual = int(producto["stock_actual"] or 0)
                    if stock_actual < cantidad:
                        raise _VentaError(
                            f"Stock insuficiente de '{producto['nombre']}'. "
                            f"Disponible: {stock_actual}, solicitado: {cantidad}"
                        )

                    precio = _money(producto["precio"])
                    subtotal = _money(precio * cantidad)
                    total += subtotal
                    nuevo_stock = stock_actual - cantidad
                    nombres.append(f"{producto['nombre']} x{cantidad}")

                    cur.execute(
                        """
                        INSERT INTO venta_detalle
                            (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (venta_id, producto_id, cantidad, precio, subtotal),
                    )
                    cur.execute(
                        "UPDATE productos SET stock_actual = %s WHERE id = %s",
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
                            f"VENTA {venta_id}",
                        ),
                    )

                cur.execute(
                    "UPDATE ventas SET total = %s WHERE id = %s RETURNING *",
                    (total, venta_id),
                )
                venta = cur.fetchone()

                descripcion = (
                    f"Venta a {cliente['nombre']} por ${total} "
                    f"({', '.join(nombres)})"
                )
                cur.execute(
                    """
                    INSERT INTO bitacora (usuario_id, accion, detalles)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        usuario_local,
                        "VENTA",
                        Json({"descripcion": descripcion, "venta_id": str(venta_id)}),
                    ),
                )

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
    def _normalizar_items(items: list[dict]) -> list[dict]:
        """Agrupa cantidades del mismo producto y descarta líneas inválidas."""
        agrupado: dict[str, int] = {}
        for item in items or []:
            producto_id = _as_id(item.get("producto_id"))
            try:
                cantidad = int(item.get("cantidad") or 0)
            except (TypeError, ValueError):
                continue
            if not producto_id or cantidad <= 0:
                continue
            agrupado[producto_id] = agrupado.get(producto_id, 0) + cantidad

        return [
            {"producto_id": pid, "cantidad": cant} for pid, cant in agrupado.items()
        ]

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
