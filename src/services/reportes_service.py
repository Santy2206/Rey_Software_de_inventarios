"""
Servicio de Reportes.

Orquesta la generación de reportes:
  1. Consulta los servicios de negocio existentes.
  2. Parsea los datos con los parsers de src.reports.parsers.
  3. Entrega los datos listos para la vista o para exportación.

Mismo contrato que el resto de servicios:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - Si hay datos, los incluye bajo la llave 'data'
  - SIN importaciones de Flet — solo lógica pura
"""

from src.services.bodegas_service import BodegasService
from src.services.productos_service import ProductosService
from src.services.ventas_service import VentasService
from src.reports.parsers.data_parser import (
    parse_bodegas_productos,
    parse_ventas_realizadas,
    parse_ventas_resumen,
    parse_productos_por_bodega,
)
from src.reports.generators.table_generator import generar_csv, generar_excel


_TIPOS_REPORTE = {
    "Bodegas/Productos",
    "Ventas",
    "Ventas Realizadas",
    "Productos por Bodega",
}


def _filtrar_por_fecha(data: list[dict], anio: int | None, mes: int | None) -> list[dict]:
    """Filtra registros con campo 'fecha' por año y/o mes."""
    if anio is None and mes is None:
        return data

    filtrados = []
    for r in data:
        fecha = r.get("fecha")
        if not fecha or not hasattr(fecha, "year"):
            continue
        if anio is not None and fecha.year != anio:
            continue
        if mes is not None and fecha.month != mes:
            continue
        filtrados.append(r)
    return filtrados


class ReportesService:
    @staticmethod
    def generar(tipo: str, anio: int | None = None, mes: int | None = None):
        """
        Genera el reporte solicitado.

        Parámetros:
            tipo: uno de 'Bodegas/Productos', 'Ventas', 'Ventas Realizadas',
                  'Productos por Bodega'
            anio: año opcional para filtrar ventas
            mes:  mes opcional (1-12) para filtrar ventas

        Retorna:
            dict: contrato estándar; 'data' contiene {'filas': [...], 'tipo': ...}
        """
        print(f"--- Generando reporte: {tipo} ---")

        if tipo not in _TIPOS_REPORTE:
            return {
                "success": False,
                "message": f"Tipo de reporte no soportado: {tipo}",
            }

        try:
            if tipo == "Bodegas/Productos":
                res = ProductosService.get_all()
                if not res.get("success"):
                    return res
                filas = parse_bodegas_productos(res.get("data", []))
                return {
                    "success": True,
                    "message": f"Reporte '{tipo}' generado",
                    "data": {"tipo": tipo, "filas": filas},
                }

            if tipo == "Ventas Realizadas":
                res = VentasService.get_all()
                if not res.get("success"):
                    return res
                ventas = _filtrar_por_fecha(res.get("data", []), anio, mes)
                filas = parse_ventas_realizadas(ventas)
                return {
                    "success": True,
                    "message": f"Reporte '{tipo}' generado",
                    "data": {"tipo": tipo, "filas": filas},
                }

            if tipo == "Ventas":
                res = VentasService.get_all()
                if not res.get("success"):
                    return res
                ventas = _filtrar_por_fecha(res.get("data", []), anio, mes)
                filas = parse_ventas_resumen(ventas)
                return {
                    "success": True,
                    "message": f"Reporte '{tipo}' generado",
                    "data": {"tipo": tipo, "filas": filas},
                }

            if tipo == "Productos por Bodega":
                res_b = BodegasService.get_all()
                res_p = ProductosService.get_all()
                if not res_b.get("success"):
                    return res_b
                if not res_p.get("success"):
                    return res_p
                filas = parse_productos_por_bodega(
                    res_b.get("data", []), res_p.get("data", [])
                )
                return {
                    "success": True,
                    "message": f"Reporte '{tipo}' generado",
                    "data": {"tipo": tipo, "filas": filas},
                }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ReportesService.generar: {error_msg}")
            return {
                "success": False,
                "message": f"Error al generar reporte: {error_msg}",
            }

    @staticmethod
    def exportar(
        tipo: str,
        formato: str,
        anio: int | None = None,
        mes: int | None = None,
        ruta: str | None = None,
    ):
        """
        Genera el reporte solicitado y lo exporta a CSV o Excel.

        Parámetros:
            tipo:    tipo de reporte (mismos valores que generar)
            formato: 'csv' o 'xlsx'
            anio:    año opcional para filtrar ventas
            mes:     mes opcional (1-12) para filtrar ventas
            ruta:    ruta destino opcional; si no se envía, se guarda en Downloads

        Retorna:
            dict: contrato estándar; 'data' contiene la ruta del archivo.
        """
        print(f"--- Exportando reporte: {tipo} ({formato}) ---")

        try:
            res = ReportesService.generar(tipo, anio, mes)
            if not res.get("success"):
                return res

            filas = res["data"]["filas"]
            if not filas:
                return {
                    "success": False,
                    "message": "No hay datos para exportar",
                }

            if formato == "csv":
                ruta_final = generar_csv(filas, ruta=ruta, tipo=tipo)
            elif formato == "xlsx":
                ruta_final = generar_excel(filas, ruta=ruta, tipo=tipo)
            else:
                return {
                    "success": False,
                    "message": f"Formato no soportado: {formato}",
                }

            return {
                "success": True,
                "message": f"Archivo guardado en {ruta_final}",
                "data": ruta_final,
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en ReportesService.exportar: {error_msg}")
            return {
                "success": False,
                "message": f"Error al exportar: {error_msg}",
            }
