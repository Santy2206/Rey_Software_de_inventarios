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


def _registrar_bitacora_stock(
    accion: str, producto_id: str, detalle: str, usuario_id: str
):
    """Registra en bitácora sin afectar la operación principal."""
    try:
        if usuario_id:
            BitacoraService.registrar(
                usuario_id,
                accion,
                entidad="producto",
                entidad_id=producto_id,
                detalle=detalle,
            )
    except Exception as e:
        print(f" Error al registrar bitácora de stock: {e}")


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
                print("No hay movimientos registrados aún")
                return {
                    "success": True,
                    "message": "No hay movimientos registrados",
                    "data": [],
                }

            print(f"Se encontraron {len(data)} movimiento(s)")
            return {
                "success": True,
                "message": "Movimientos obtenidos",
                "data": data,
            }

        except Exception as e:
            error_msg = str(e)
            print(f"Error en MovimientosService.get_all: {error_msg}")
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
            print(f"Error en MovimientosService.get_by_producto: {error_msg}")
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
            f"Movimiento registrado: {tipo} de {cantidad} unidades de '{nombre_producto}'"
        )
        print(f"   Stock anterior: {stock_actual} → Stock nuevo: {nuevo_stock}")

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
            print(f"Error en registrar_entrada: {error_msg}")
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
            print(f"Error en registrar_salida: {error_msg}")
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
            resultado = MovimientosService._registrar_movimiento(
                producto_id, bodega_id, "egreso", cantidad, motivo, usuario_id
            )
            if resultado.get("success"):
                _registrar_bitacora_stock(
                    "AJUSTE_STOCK",
                    producto_id,
                    f"Ajuste de stock: -{cantidad} unidades. Motivo: {motivo}",
                    usuario_id,
                )
            return resultado
        except Exception as e:
            error_msg = str(e)
            print(f"Error en registrar_ajuste: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar ajuste: {error_msg}",
            }

    @staticmethod
    def registrar_preparacion(
        producto_esencia_id: str,
        cantidad_ml: float,
        motivo: str,
        usuario_id: str,
    ):
        """
        Registra la PREPARACIÓN de una fragancia terminada.

        Flujo (una sola transacción):
          1. Egreso de esencia_g gramos del producto en 'Venta Fragancias'.
             esencia_g = MEZCLA_ML_A_GRAMOS[cantidad_ml].
          2. Egreso de alcohol_g gramos del producto genérico de la
             bodega 'Alcohol'. alcohol_g = cantidad_ml - esencia_g.
          3. Ingreso de cantidad_ml gramos al producto con el mismo
             código en 'Fragancias Terminado' (se crea si no existe).

        Si falta stock en esencia o alcohol, aborta sin tocar nada.
        """
        from src.services.elisa_concepto_parser import gramos_esencia_por_ml

        print(f"--- Registrando PREPARACIÓN de {cantidad_ml} ml ---")
        try:
            esencia_g = gramos_esencia_por_ml(cantidad_ml)
            if esencia_g is None:
                return {
                    "success": False,
                    "message": (
                        f"No hay regla de mezcla para {cantidad_ml} ml "
                        "(tamaños válidos: 20–125 ml)."
                    ),
                }
            alcohol_g = round(float(cantidad_ml) - esencia_g, 4)
            total_g = round(float(cantidad_ml), 4)

            with get_cursor() as cur:
                # 1) Producto esencia (debe estar en Venta Fragancias)
                cur.execute(
                    """
                    SELECT p.id, p.nombre, p.codigo, p.stock_actual,
                           b.nombre AS bodega_nombre, p.bodega_id
                    FROM productos p
                    JOIN bodegas b ON b.id = p.bodega_id
                    WHERE p.id = %s
                    FOR UPDATE OF p
                    """,
                    (producto_esencia_id,),
                )
                esencia = cur.fetchone()
                if not esencia:
                    return {"success": False, "message": "Producto esencia no encontrado"}
                if "VENTA" not in (esencia["bodega_nombre"] or "").upper():
                    return {
                        "success": False,
                        "message": (
                            "La esencia debe estar en la bodega "
                            f"'Venta Fragancias' (está en '{esencia['bodega_nombre']}')."
                        ),
                    }
                if esencia["stock_actual"] < esencia_g:
                    return {
                        "success": False,
                        "message": (
                            f"Esencia insuficiente: hay {esencia['stock_actual']} g, "
                            f"se necesitan {esencia_g} g."
                        ),
                    }

                # 2) Producto alcohol genérico en bodega 'Alcohol'
                cur.execute(
                    """
                    SELECT p.id, p.nombre, p.stock_actual
                    FROM productos p
                    JOIN bodegas b ON b.id = p.bodega_id
                    WHERE UPPER(b.nombre) = 'ALCOHOL'
                    ORDER BY p.nombre
                    LIMIT 1
                    FOR UPDATE OF p
                    """,
                )
                alcohol = cur.fetchone()
                if not alcohol:
                    return {
                        "success": False,
                        "message": "No hay producto de alcohol en la bodega 'Alcohol'",
                    }
                if alcohol["stock_actual"] < alcohol_g:
                    return {
                        "success": False,
                        "message": (
                            f"Alcohol insuficiente: hay {alcohol['stock_actual']} g, "
                            f"se necesitan {alcohol_g} g."
                        ),
                    }

                # 3) Bodega 'Fragancias Terminado' + producto destino
                cur.execute(
                    "SELECT id FROM bodegas WHERE UPPER(nombre) LIKE '%TERMINADO%' LIMIT 1"
                )
                bodega_term = cur.fetchone()
                if not bodega_term:
                    return {
                        "success": False,
                        "message": "No existe la bodega 'Fragancias Terminado'",
                    }
                codigo = (esencia.get("codigo") or "").strip().upper()
                if not codigo:
                    return {
                        "success": False,
                        "message": "El producto esencia no tiene código asignado",
                    }

                cur.execute(
                    """
                    SELECT id, stock_actual FROM productos
                    WHERE bodega_id = %s AND UPPER(codigo) = %s
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (bodega_term["id"], codigo),
                )
                terminado = cur.fetchone()
                if not terminado:
                    cur.execute(
                        """
                        INSERT INTO productos
                            (bodega_id, nombre, codigo, stock_actual, dirty)
                        VALUES (%s, %s, %s, 0, true)
                        RETURNING id, stock_actual
                        """,
                        (
                            bodega_term["id"],
                            f"{codigo} TERMINADO",
                            codigo,
                        ),
                    )
                    terminado = cur.fetchone()

                motivo_txt = motivo or (
                    f"Preparación {cantidad_ml} ml: -{esencia_g}g esencia, "
                    f"-{alcohol_g}g alcohol → {total_g}g en Terminado"
                )

                def _mov(prod_id, bodega_id, tipo, cantidad, detalle):
                    cur.execute(
                        """
                        INSERT INTO movimientos
                            (producto_id, bodega_id, usuario_id, tipo, cantidad, motivo, fecha)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (prod_id, bodega_id, usuario_id, tipo, cantidad, detalle),
                    )

                # Egreso esencia
                _mov(
                    esencia["id"], esencia["bodega_id"], "egreso", esencia_g,
                    f"Preparación {codigo}: -{esencia_g}g esencia ({motivo_txt})",
                )
                cur.execute(
                    "UPDATE productos SET stock_actual = stock_actual - %s, dirty = true WHERE id = %s",
                    (esencia_g, esencia["id"]),
                )
                # Egreso alcohol
                cur.execute(
                    "SELECT bodega_id FROM productos WHERE id = %s",
                    (alcohol["id"],),
                )
                _mov(
                    alcohol["id"],
                    cur.fetchone()["bodega_id"],
                    "egreso",
                    alcohol_g,
                    f"Preparación {codigo}: -{alcohol_g}g alcohol ({motivo_txt})",
                )
                cur.execute(
                    "UPDATE productos SET stock_actual = stock_actual - %s, dirty = true WHERE id = %s",
                    (alcohol_g, alcohol["id"]),
                )
                # Ingreso a Terminado
                _mov(
                    terminado["id"], bodega_term["id"], "ingreso", total_g,
                    f"Preparación {codigo}: +{total_g}g ({motivo_txt})",
                )
                cur.execute(
                    "UPDATE productos SET stock_actual = stock_actual + %s, dirty = true WHERE id = %s",
                    (total_g, terminado["id"]),
                )

            print(
                f"Preparación {codigo}: -{esencia_g}g esencia, "
                f"-{alcohol_g}g alcohol, +{total_g}g terminado"
            )
            _registrar_bitacora_stock(
                "PREPARACION",
                terminado["id"],
                f"Preparación {codigo} {cantidad_ml}ml: "
                f"-{esencia_g}g esencia, -{alcohol_g}g alcohol",
                usuario_id,
            )
            return {
                "success": True,
                "message": (
                    f"Preparación lista: {codigo} {cantidad_ml} ml "
                    f"(-{esencia_g}g esencia, -{alcohol_g}g alcohol)"
                ),
            }
        except Exception as e:
            error_msg = str(e)
            print(f"Error en registrar_preparacion: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar preparación: {error_msg}",
            }

    @staticmethod
    def registrar_traslado(
        producto_id: str,
        bodega_destino_id: str,
        cantidad: float,
        motivo: str,
        usuario_id: str,
    ):
        """
        Traslada stock de un producto a OTRA bodega en una transacción:
          1. Egreso del producto en su bodega actual.
          2. Ingreso del producto equivalente (mismo código) en la bodega
             destino; se crea si no existe.

        Ej: pasar 200 g de esencia '20M' de Fragancias Bodega a Venta
        Fragancias.
        """
        print(f"--- Registrando TRASLADO de {cantidad} unidades ---")
        try:
            with get_cursor() as cur:
                cur.execute(
                    """
                    SELECT p.id, p.nombre, p.codigo, p.precio, p.descripcion,
                           p.stock_actual, p.bodega_id, b.nombre AS bodega_nombre
                    FROM productos p
                    JOIN bodegas b ON b.id = p.bodega_id
                    WHERE p.id = %s
                    FOR UPDATE OF p
                    """,
                    (producto_id,),
                )
                origen = cur.fetchone()
                if not origen:
                    return {"success": False, "message": "Producto no encontrado"}

                if str(origen["bodega_id"]) == str(bodega_destino_id):
                    return {
                        "success": False,
                        "message": "La bodega destino debe ser distinta a la de origen",
                    }

                if origen["stock_actual"] < cantidad:
                    return {
                        "success": False,
                        "message": (
                            f"Stock insuficiente en {origen['bodega_nombre']}: "
                            f"hay {origen['stock_actual']}, se piden {cantidad}."
                        ),
                    }

                # Producto destino: mismo código (o mismo nombre si no hay código)
                cur.execute(
                    """
                    SELECT id, stock_actual FROM productos
                    WHERE bodega_id = %s
                      AND (
                          (codigo IS NOT NULL AND codigo != ''
                           AND UPPER(codigo) = UPPER(%s))
                          OR UPPER(nombre) = UPPER(%s)
                      )
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (bodega_destino_id, origen.get("codigo") or "\x00",
                     origen["nombre"]),
                )
                destino = cur.fetchone()
                if not destino:
                    cur.execute(
                        """
                        INSERT INTO productos
                            (bodega_id, nombre, codigo, precio, descripcion,
                             stock_actual, dirty)
                        VALUES (%s, %s, %s, %s, %s, 0, true)
                        RETURNING id, stock_actual
                        """,
                        (
                            bodega_destino_id,
                            origen["nombre"],
                            origen.get("codigo"),
                            origen.get("precio"),
                            origen.get("descripcion"),
                        ),
                    )
                    destino = cur.fetchone()

                motivo_txt = motivo or (
                    f"Traslado {origen['bodega_nombre']} → destino"
                )

                # Egreso origen (tipo 'transferencia' por el CHECK constraint)
                cur.execute(
                    """
                    INSERT INTO movimientos
                        (producto_id, bodega_id, usuario_id, tipo,
                         cantidad, motivo, fecha)
                    VALUES (%s, %s, %s, 'transferencia', %s, %s, NOW())
                    """,
                    (origen["id"], origen["bodega_id"], usuario_id,
                     cantidad, f"Traslado salida: {motivo_txt}"),
                )
                cur.execute(
                    "UPDATE productos SET stock_actual = stock_actual - %s, dirty = true WHERE id = %s",
                    (cantidad, origen["id"]),
                )
                # Ingreso destino
                cur.execute(
                    """
                    INSERT INTO movimientos
                        (producto_id, bodega_id, usuario_id, tipo,
                         cantidad, motivo, fecha)
                    VALUES (%s, %s, %s, 'transferencia', %s, %s, NOW())
                    """,
                    (destino["id"], bodega_destino_id, usuario_id,
                     cantidad, f"Traslado entrada: {motivo_txt}"),
                )
                cur.execute(
                    "UPDATE productos SET stock_actual = stock_actual + %s, dirty = true WHERE id = %s",
                    (cantidad, destino["id"]),
                )

            _registrar_bitacora_stock(
                "TRASLADO",
                str(destino["id"]),
                f"Traslado de {cantidad} desde {origen['bodega_nombre']} "
                f"({origen['nombre']})",
                usuario_id,
            )
            return {
                "success": True,
                "message": (
                    f"Traslado OK: {cantidad} de '{origen['nombre']}' "
                    f"→ bodega destino"
                ),
            }
        except Exception as e:
            error_msg = str(e)
            print(f"Error en registrar_traslado: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar traslado: {error_msg}",
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
            resultado = MovimientosService._registrar_movimiento(
                producto_id, bodega_id, "egreso", cantidad, motivo, usuario_id
            )
            if resultado.get("success"):
                _registrar_bitacora_stock(
                    "BAJA_STOCK",
                    producto_id,
                    f"Baja de stock: -{cantidad} unidades. Motivo: {motivo}",
                    usuario_id,
                )
            return resultado
        except Exception as e:
            error_msg = str(e)
            print(f"Error en registrar_baja: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar baja: {error_msg}",
            }
