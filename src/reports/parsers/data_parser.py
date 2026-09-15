"""
Parsers de datos para reportes.

Convierten los resultados crudos de los servicios en listas de dicts
planos y listos para ser exportados a CSV/Excel.

Reglas:
    - Entrada: listas de dicts (resultados de services).
    - Salida: listas de dicts normalizados.
    - SIN importaciones de Flet.
    - SIN llamadas a base de datos.
"""

from decimal import Decimal


def _money(value) -> float:
    """Convierte precios/valores a float redondeado a 2 decimales."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value.quantize(Decimal("0.01")))
    return float(value)


def _fecha_str(value) -> str:
    if value is None:
        return "—"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value)


def parse_bodegas_productos(productos: list[dict]) -> list[dict]:
    """Reporte Bodegas/Productos: inventario con valor por producto."""
    filas = []
    for p in productos or []:
        precio = _money(p.get("precio"))
        stock = int(p.get("stock_actual") or 0)
        filas.append(
            {
                "Bodega": p.get("bodega_nombre") or "—",
                "Producto": p.get("nombre") or "—",
                "SKU": p.get("sku") or "—",
                "Precio Unitario": precio,
                "Stock Actual": stock,
                "Valor Total": round(precio * stock, 2),
            }
        )
    return filas


def parse_ventas_realizadas(ventas: list[dict]) -> list[dict]:
    """Reporte Ventas Realizadas: detalle de cada venta."""
    filas = []
    for v in ventas or []:
        total = _money(v.get("total"))
        filas.append(
            {
                "Fecha": _fecha_str(v.get("fecha")),
                "Cliente": v.get("cliente_nombre") or "—",
                "Items": v.get("items") or 0,
                "Unidades": v.get("unidades") or 0,
                "Total": total,
                "Vendedor": v.get("usuario_nombre") or "—",
            }
        )
    return filas


def parse_ventas_resumen(ventas: list[dict]) -> list[dict]:
    """Reporte Ventas: resumen agregado por cliente."""
    resumen: dict[str, dict] = {}
    for v in ventas or []:
        cliente = v.get("cliente_nombre") or "—"
        if cliente not in resumen:
            resumen[cliente] = {
                "Cliente": cliente,
                "Cantidad de Ventas": 0,
                "Unidades Vendidas": 0,
                "Total": 0.0,
            }
        resumen[cliente]["Cantidad de Ventas"] += 1
        resumen[cliente]["Unidades Vendidas"] += int(v.get("unidades") or 0)
        resumen[cliente]["Total"] += _money(v.get("total"))

    for r in resumen.values():
        r["Total"] = round(r["Total"], 2)

    return sorted(resumen.values(), key=lambda x: x["Total"], reverse=True)


def parse_productos_por_bodega(bodegas: list[dict], productos: list[dict]) -> list[dict]:
    """Reporte Productos por Bodega: listado de productos agrupado por bodega."""
    filas = []
    for b in bodegas or []:
        productos_bodega = [
            p for p in (productos or []) if p.get("bodega_id") == b.get("id")
        ]
        for p in productos_bodega:
            precio = _money(p.get("precio"))
            stock = int(p.get("stock_actual") or 0)
            filas.append(
                {
                    "Bodega": b.get("nombre") or "—",
                    "Producto": p.get("nombre") or "—",
                    "SKU": p.get("sku") or "—",
                    "Precio Unitario": precio,
                    "Stock Actual": stock,
                    "Valor Total": round(precio * stock, 2),
                }
            )
    return filas
