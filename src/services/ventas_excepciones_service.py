"""
Reporte consolidado de excepciones de importación Elisa (Fase 5).

Agrupa lo que sigue pendiente de decisión humana o informativo:

  1. productos_pendientes     — estado_resolucion = pendiente
  2. conflictos_cliente       — estado_cliente = conflicto
  3. errores_proceso          — estado_proceso = error
  4. sobrantes_caja           — es_cuadre_caja = true (41353899)
  5. duplicados_omitidos      — es_duplicado_omitido = true
  6. stock_negativo           — productos.stock_actual < 0

Solo consolida y hace visible; no resuelve automáticamente nada.
SIN imports de Flet.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from src.core.local_db import run_query


def _fmt_qty(value) -> str:
    """Muestra cantidades numeric(14,4) sin basura de ceros."""
    try:
        d = Decimal(str(value if value is not None else 0))
        d = d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        s = f"{d:.4f}".rstrip("0").rstrip(".")
        return s if s else "0"
    except Exception:
        return str(value)


class VentasExcepcionesService:
    """Vista consolidada de excepciones post-importación Elisa."""

    CATEGORIAS = (
        "productos_pendientes",
        "conflictos_cliente",
        "errores_proceso",
        "sobrantes_caja",
        "duplicados_omitidos",
        "stock_negativo",
    )

    @staticmethod
    def resumen(lote_id: str | None = None) -> dict:
        """Conteos de las 6 categorías."""
        try:
            params: list = []
            filtro_lote = ""
            if lote_id:
                filtro_lote = " AND lote_id = %s"
                params.append(lote_id)

            def _count(sql_extra: str, extra_params: tuple = ()):
                qparams = list(params) + list(extra_params)
                row = run_query(
                    f"""
                    SELECT COUNT(*) AS n
                    FROM ventas_import_raw
                    WHERE 1=1 {filtro_lote} {sql_extra}
                    """,
                    tuple(qparams) if qparams else (),
                    fetch_one=True,
                )
                return int(row["n"] or 0) if row else 0

            productos_pendientes = _count(
                " AND estado_resolucion = 'pendiente'"
                " AND COALESCE(es_duplicado_omitido, false) = false"
                " AND es_cuadre_caja = false"
            )
            conflictos_cliente = _count(
                " AND estado_cliente = 'conflicto'"
                " AND COALESCE(es_duplicado_omitido, false) = false"
            )
            errores_proceso = _count(
                " AND estado_proceso = 'error'"
                " AND COALESCE(es_duplicado_omitido, false) = false"
            )
            sobrantes = _count(" AND es_cuadre_caja = true")
            duplicados = _count(
                " AND (es_duplicado_omitido = true"
                " OR estado_proceso = 'duplicado_omitido')"
            )

            stock_neg = run_query(
                """
                SELECT COUNT(*) AS n
                FROM productos
                WHERE stock_actual < 0
                """,
                fetch_one=True,
            )
            stock_negativo = int(stock_neg["n"] or 0) if stock_neg else 0

            data = {
                "lote_id": lote_id,
                "productos_pendientes": productos_pendientes,
                "conflictos_cliente": conflictos_cliente,
                "errores_proceso": errores_proceso,
                "sobrantes_caja": sobrantes,
                "duplicados_omitidos": duplicados,
                "stock_negativo": stock_negativo,
                "total_excepciones": (
                    productos_pendientes
                    + conflictos_cliente
                    + errores_proceso
                    + sobrantes
                    + duplicados
                    + stock_negativo
                ),
            }
            return {
                "success": True,
                "message": f"{data['total_excepciones']} excepción(es) total",
                "data": data,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al resumir excepciones: {e}",
                "data": None,
            }

    @staticmethod
    def get_detalle(
        categoria: str,
        lote_id: str | None = None,
        limite: int = 200,
    ) -> dict:
        """
        Lista detalle navegable de una categoría.

        categoria: una de CATEGORIAS
        """
        try:
            if categoria not in VentasExcepcionesService.CATEGORIAS:
                return {
                    "success": False,
                    "message": f"Categoría no válida: {categoria}",
                    "data": [],
                }

            if categoria == "stock_negativo":
                rows = run_query(
                    """
                    SELECT p.id, p.nombre, p.codigo, p.stock_actual,
                           p.bodega_id, b.nombre AS bodega_nombre
                    FROM productos p
                    LEFT JOIN bodegas b ON b.id = p.bodega_id
                    WHERE p.stock_actual < 0
                    ORDER BY p.stock_actual ASC, p.nombre
                    LIMIT %s
                    """,
                    (limite,),
                )
                data = []
                for r in rows or []:
                    data.append(
                        {
                            "id": str(r["id"]),
                            "nombre": r.get("nombre"),
                            "codigo": r.get("codigo"),
                            "stock_actual": _fmt_qty(r.get("stock_actual")),
                            "stock_actual_raw": float(r.get("stock_actual") or 0),
                            "bodega_id": str(r["bodega_id"]) if r.get("bodega_id") else None,
                            "bodega_nombre": r.get("bodega_nombre"),
                        }
                    )
                return {
                    "success": True,
                    "message": f"{len(data)} producto(s) con stock negativo",
                    "data": data,
                }

            params: list = []
            where = "WHERE 1=1"
            if lote_id:
                where += " AND r.lote_id = %s"
                params.append(lote_id)

            if categoria == "productos_pendientes":
                where += (
                    " AND r.estado_resolucion = 'pendiente'"
                    " AND COALESCE(r.es_duplicado_omitido, false) = false"
                    " AND r.es_cuadre_caja = false"
                )
            elif categoria == "conflictos_cliente":
                where += (
                    " AND r.estado_cliente = 'conflicto'"
                    " AND COALESCE(r.es_duplicado_omitido, false) = false"
                )
            elif categoria == "errores_proceso":
                where += (
                    " AND r.estado_proceso = 'error'"
                    " AND COALESCE(r.es_duplicado_omitido, false) = false"
                )
            elif categoria == "sobrantes_caja":
                where += " AND r.es_cuadre_caja = true"
            elif categoria == "duplicados_omitidos":
                where += (
                    " AND (r.es_duplicado_omitido = true"
                    " OR r.estado_proceso = 'duplicado_omitido')"
                )

            params.append(limite)
            rows = run_query(
                f"""
                SELECT r.id, r.lote_id, r.fila_origen, r.fecha, r.cuenta,
                       r.concepto, r.identidad, r.nombre_tercero, r.credito,
                       r.concepto_limpio, r.cantidad, r.atributos,
                       r.estado_resolucion, r.estado_cliente, r.estado_proceso,
                       r.error_proceso, r.clave_busqueda, r.candidatos,
                       r.conflicto_cliente, r.codigo_elisa,
                       r.nombre_cliente_limpio, r.huella,
                       r.es_duplicado_omitido, r.es_cuadre_caja,
                       r.venta_id, r.procesado
                FROM ventas_import_raw r
                {where}
                ORDER BY r.creado_en DESC, r.fila_origen
                LIMIT %s
                """,
                tuple(params),
            )
            return {
                "success": True,
                "message": f"{len(rows or [])} fila(s)",
                "data": rows or [],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al listar detalle: {e}",
                "data": [],
            }

    @staticmethod
    def reporte_completo(lote_id: str | None = None, limite_por_cat: int = 100) -> dict:
        """Resumen + detalle de las 6 categorías en un solo payload."""
        try:
            res = VentasExcepcionesService.resumen(lote_id)
            if not res.get("success"):
                return res
            detalle = {}
            for cat in VentasExcepcionesService.CATEGORIAS:
                d = VentasExcepcionesService.get_detalle(
                    cat, lote_id=lote_id, limite=limite_por_cat
                )
                detalle[cat] = d.get("data") or []
            return {
                "success": True,
                "message": res["message"],
                "data": {
                    "resumen": res["data"],
                    "detalle": detalle,
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al generar reporte: {e}",
                "data": None,
            }
