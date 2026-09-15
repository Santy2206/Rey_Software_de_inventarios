"""
Generadores de reportes.

Reciben datos ya parseados (lista de dicts) y producen archivos CSV o Excel.

Convenciones:
    - Cada generador recibe datos procesados.
    - Retorna la ruta del archivo generado.
    - SIN importaciones de Flet.
    - SIN llamadas a base de datos.
"""

import csv
import os
from datetime import datetime

import pandas as pd


def _ruta_salida(tipo: str, formato: str, ruta: str | None = None) -> str:
    if ruta:
        return ruta

    base = os.path.expanduser("~")
    carpeta = os.path.join(base, "Downloads")
    os.makedirs(carpeta, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_tipo = tipo.lower().replace(" ", "_").replace("/", "_")
    nombre = f"reporte_{nombre_tipo}_{timestamp}.{formato}"
    return os.path.join(carpeta, nombre)


def generar_csv(filas: list[dict], ruta: str | None = None, tipo: str = "reporte") -> str:
    """Genera un archivo CSV a partir de una lista de dicts."""
    if not filas:
        raise ValueError("No hay filas para exportar")

    ruta_final = _ruta_salida(tipo, "csv", ruta)

    with open(ruta_final, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=filas[0].keys())
        writer.writeheader()
        writer.writerows(filas)

    return ruta_final


def generar_excel(filas: list[dict], ruta: str | None = None, tipo: str = "reporte") -> str:
    """Genera un archivo Excel (.xlsx) a partir de una lista de dicts."""
    if not filas:
        raise ValueError("No hay filas para exportar")

    ruta_final = _ruta_salida(tipo, "xlsx", ruta)

    df = pd.DataFrame(filas)
    df.to_excel(ruta_final, index=False, engine="openpyxl")

    return ruta_final
