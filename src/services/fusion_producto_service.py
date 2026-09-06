"""
Fusión de productos duplicados (Fase 2).

Operación destructiva e irreversible: mueve todas las referencias del
producto origen al destino y elimina el origen, en UNA sola transacción.

Protecciones obligatorias (mismo espíritu que ELIMINACION):
  1. Re-autenticar con la contraseña del usuario de la sesión actual
     (AuthService.verificar_password_sesion — PostgreSQL local).
  2. La palabra de confirmación debe ser exactamente PALABRA_CONFIRMACION
     (constante fácil de ajustar; por defecto "FUSIONAR").
  3. Registrar FUSION_PRODUCTO en bitácora.

Tablas con FK a productos (verificado en esquema real):
  - movimientos.producto_id   (ON DELETE CASCADE)
  - venta_detalle.producto_id (ON DELETE RESTRICT)
  - ventas_import_raw.producto_id (sin FK formal; se actualiza igual)

SIN imports de Flet.
"""

from __future__ import annotations

from src.core.local_db import get_cursor
from src.services.auth_service import AuthService
from src.services.bitacora_service import BitacoraService


# Palabra exacta requerida además de la contraseña.
# Ajustar aquí si el negocio prefiere otra (ej. el nombre del destino).
PALABRA_CONFIRMACION = "FUSIONAR"


class FusionProductoService:
    """Fusiona dos productos del catálogo con protecciones de seguridad."""

    @staticmethod
    def fusionar(
        producto_origen_id: str,
        producto_destino_id: str,
        password: str,
        palabra_confirmacion: str,
        usuario_id: str | None = None,
    ) -> dict:
        """
        Fusiona producto_origen → producto_destino.

        Parámetros:
            producto_origen_id:  el que se elimina (duplicado)
            producto_destino_id: el que se conserva
            password:            contraseña del usuario de la sesión
            palabra_confirmacion: debe ser exactamente PALABRA_CONFIRMACION
            usuario_id:          opcional; si no se pasa se usa la sesión

        Retorna contrato estándar.
        """
        print(
            f"--- Fusionando producto {producto_origen_id} -> {producto_destino_id} ---"
        )
        try:
            if not producto_origen_id or not producto_destino_id:
                return {
                    "success": False,
                    "message": "Origen y destino son obligatorios",
                }
            if str(producto_origen_id) == str(producto_destino_id):
                return {
                    "success": False,
                    "message": "Origen y destino deben ser productos distintos",
                }

            # 1) Re-autenticación
            auth = AuthService.verificar_password_sesion(password)
            if not auth.get("success"):
                return {
                    "success": False,
                    "message": auth.get("message") or "Contraseña incorrecta",
                }

            # 2) Palabra de confirmación
            if (palabra_confirmacion or "").strip() != PALABRA_CONFIRMACION:
                return {
                    "success": False,
                    "message": (
                        f"Palabra de confirmación incorrecta. "
                        f'Debe escribir exactamente "{PALABRA_CONFIRMACION}"'
                    ),
                }

            uid = usuario_id or AuthService.get_usuario_id()
            if not uid:
                return {
                    "success": False,
                    "message": "No hay sesión activa para auditar la fusión",
                }

            with get_cursor() as cur:
                cur.execute(
                    "SELECT id, nombre, codigo, stock_actual FROM productos WHERE id = %s FOR UPDATE",
                    (producto_origen_id,),
                )
                origen = cur.fetchone()
                cur.execute(
                    "SELECT id, nombre, codigo, stock_actual FROM productos WHERE id = %s FOR UPDATE",
                    (producto_destino_id,),
                )
                destino = cur.fetchone()

                if not origen:
                    return {"success": False, "message": "Producto origen no encontrado"}
                if not destino:
                    return {"success": False, "message": "Producto destino no encontrado"}

                # 3a) Mover referencias en movimientos
                cur.execute(
                    """
                    UPDATE movimientos
                    SET producto_id = %s, dirty = true
                    WHERE producto_id = %s
                    """,
                    (producto_destino_id, producto_origen_id),
                )
                movs = cur.rowcount or 0

                # 3b) Mover referencias en venta_detalle
                #     (puede haber conflicto de unique si no existe;
                #      el esquema actual no define unique (venta_id, producto_id))
                cur.execute(
                    """
                    UPDATE venta_detalle
                    SET producto_id = %s
                    WHERE producto_id = %s
                    """,
                    (producto_destino_id, producto_origen_id),
                )
                dets = cur.rowcount or 0

                # 3c) Mover vínculos de importación
                cur.execute(
                    """
                    UPDATE ventas_import_raw
                    SET producto_id = %s
                    WHERE producto_id = %s
                    """,
                    (producto_destino_id, producto_origen_id),
                )
                imports = cur.rowcount or 0

                # 3d) Sumar stock del origen al destino
                stock_origen = int(origen.get("stock_actual") or 0)
                if stock_origen:
                    cur.execute(
                        """
                        UPDATE productos
                        SET stock_actual = stock_actual + %s,
                            dirty = true
                        WHERE id = %s
                        """,
                        (stock_origen, producto_destino_id),
                    )

                # 4) Eliminar origen
                cur.execute(
                    "DELETE FROM productos WHERE id = %s RETURNING id",
                    (producto_origen_id,),
                )
                borrado = cur.fetchone()
                if not borrado:
                    return {
                        "success": False,
                        "message": "No se pudo eliminar el producto origen",
                    }

            # 5) Bitácora (fuera de la TX de datos: no bloquea la fusión si falla)
            BitacoraService.registrar(
                uid,
                "FUSION_PRODUCTO",
                entidad="producto",
                entidad_id=producto_destino_id,
                detalle=(
                    f"Fusionado '{origen.get('nombre')}' "
                    f"({origen.get('codigo') or 's/c'}) -> "
                    f"'{destino.get('nombre')}' "
                    f"({destino.get('codigo') or 's/c'}); "
                    f"movs={movs}, det={dets}, imp={imports}, stock+={stock_origen}"
                ),
            )

            print(
                f" Fusion OK: {origen.get('nombre')} -> {destino.get('nombre')} "
                f"(movs={movs}, det={dets}, imp={imports})"
            )
            return {
                "success": True,
                "message": (
                    f"Producto '{origen.get('nombre')}' fusionado en "
                    f"'{destino.get('nombre')}'"
                ),
                "data": {
                    "origen_id": str(producto_origen_id),
                    "destino_id": str(producto_destino_id),
                    "movimientos_movidos": movs,
                    "venta_detalle_movidos": dets,
                    "import_raw_movidos": imports,
                    "stock_sumado": stock_origen,
                },
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en FusionProductoService.fusionar: {error_msg}")
            return {
                "success": False,
                "message": f"Error al fusionar productos: {error_msg}",
            }
