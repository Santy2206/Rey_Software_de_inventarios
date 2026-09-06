"""
Servicio de importación de ventas Elisa — Fase 1 + idempotencia (Fase 5).

Lee un archivo .xls/.xlsx exportado de Elisa y lo aterriza en
`ventas_import_raw` SIN perder el dato original. Para cada fila:

  1. Guarda las 7 columnas del Excel como texto (fecha, cuenta, concepto,
     identidad, nombre_tercero, telefonos_tercero, credito).
  2. Corre el parser de CONCEPTO (limpieza + atributos por cuenta).
  3. Marca es_cuadre_caja / procesado=false.
  4. Calcula huella SHA-256 (fecha+cuenta+concepto+identidad+credito+fila)
     para idempotencia:
       - si ya existe la misma huella procesada con éxito → duplicado omitido
       - si existe pero falló / quedó pendiente → se permite reintentar

SIN imports de Flet. Contrato estándar: {"success", "message", "data"}.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pandas as pd
from psycopg2.extras import Json, execute_values

from src.core.local_db import get_cursor, run_query
from src.services.elisa_concepto_parser import parsear_fila_elisa


def calcular_huella_fila(
    fecha=None,
    cuenta=None,
    concepto=None,
    identidad=None,
    credito=None,
    fila_origen=None,
) -> str:
    """
    Huella estable de una fila Elisa para detectar reimportaciones.

    Incluye fila_origen para no colapsar dos filas idénticas del mismo
    archivo (mismo concepto en dos líneas distintas).
    """
    partes = [
        str(fecha or "").strip(),
        str(cuenta or "").strip(),
        str(concepto or "").strip(),
        str(identidad or "").strip(),
        str(credito or "").strip(),
        str(fila_origen if fila_origen is not None else ""),
    ]
    raw = "|".join(partes).upper()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _buscar_huella_previa(cur, huella: str) -> dict | None:
    """
    Busca la fila más reciente con esta huella.
    Preferencia: procesada con éxito; si no, la última no omitida.
    """
    cur.execute(
        """
        SELECT id, lote_id, estado_proceso, procesado, venta_id,
               es_duplicado_omitido
        FROM ventas_import_raw
        WHERE huella = %s
          AND COALESCE(es_duplicado_omitido, false) = false
        ORDER BY
          CASE WHEN estado_proceso = 'procesado' OR procesado = true
               THEN 0 ELSE 1 END,
          creado_en DESC
        LIMIT 1
        """,
        (huella,),
    )
    return cur.fetchone()


# Encabezados posibles del archivo Elisa (normalizados sin acentos/espacios).
_COLUMNAS_ELISA = {
    "fecha": "fecha",
    "cuenta": "cuenta",
    "concepto": "concepto",
    "identidad": "identidad",
    "nombredeltercero": "nombre_tercero",
    "nombretercero": "nombre_tercero",
    "telefonosdeltercero": "telefonos_tercero",
    "telefonostercero": "telefonos_tercero",
    "telefono": "telefonos_tercero",
    "credito": "credito",
}


def _norm_header(value) -> str:
    s = "" if value is None else str(value)
    s = (
        s.upper()
        .replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
        .replace("Ñ", "N")
        # openpyxl a veces entrega mojibake de acentos
        .replace("Ã³", "O")
        .replace("Ã¡", "A")
        .replace("Ã©", "E")
        .replace("Ã­", "I")
        .replace("Ãº", "U")
        .replace("Ã±", "N")
    )
    # solo alfanumérico, en minúsculas para comparar con _COLUMNAS_ELISA
    return "".join(ch for ch in s if ch.isalnum()).lower()


def _as_text(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    texto = str(value).strip()
    if not texto or texto.lower() == "nan":
        return None
    # Evitar "41353802.0" en cuentas leídas como float
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return texto


def _mapear_columnas(df: pd.DataFrame) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for col in df.columns:
        key = _norm_header(col)
        destino = _COLUMNAS_ELISA.get(key)
        if destino is None:
            # alias parciales (acentos / nombres cortos)
            if key.startswith("fecha"):
                destino = "fecha"
            elif key.startswith("cuenta"):
                destino = "cuenta"
            elif key.startswith("concepto"):
                destino = "concepto"
            elif key.startswith("identidad"):
                destino = "identidad"
            elif "nombre" in key and "tercer" in key:
                destino = "nombre_tercero"
            elif "telefon" in key:
                destino = "telefonos_tercero"
            elif key.startswith("credito"):
                destino = "credito"
        if destino and destino not in mapping.values():
            mapping[col] = destino
    return mapping


class VentasImportService:
    """Aterrizaje de ventas Elisa en ventas_import_raw (Fase 1)."""

    @staticmethod
    def leer_archivo(ruta_archivo: str) -> dict:
        """
        Lee el .xls/.xlsx y retorna las filas crudas + mapeo de columnas.

        No escribe en base de datos.
        """
        print(f"--- Leyendo archivo Elisa: {ruta_archivo} ---")
        try:
            path = Path(ruta_archivo)
            if not path.exists():
                return {
                    "success": False,
                    "message": f"Archivo no encontrado: {ruta_archivo}",
                    "data": None,
                }

            extension = path.suffix.lower()
            if extension == ".xls":
                df = pd.read_excel(path, engine="xlrd", dtype=object)
            elif extension in (".xlsx", ".xlsm"):
                df = pd.read_excel(path, engine="openpyxl", dtype=object)
            else:
                return {
                    "success": False,
                    "message": "Formato no soportado. Use .xls o .xlsx",
                    "data": None,
                }

            if df is None or df.empty:
                return {
                    "success": False,
                    "message": "El archivo no tiene filas de datos",
                    "data": None,
                }

            mapping = _mapear_columnas(df)
            faltantes = [
                c
                for c in (
                    "fecha",
                    "cuenta",
                    "concepto",
                    "identidad",
                    "nombre_tercero",
                    "credito",
                )
                if c not in mapping.values()
            ]
            if faltantes:
                return {
                    "success": False,
                    "message": (
                        "Faltan columnas obligatorias en el archivo: "
                        + ", ".join(faltantes)
                    ),
                    "data": {
                        "columnas_detectadas": list(df.columns.astype(str)),
                        "mapeo": mapping,
                    },
                }

            filas = []
            for i, row in df.iterrows():
                # Excel 1-based + encabezado ≈ fila_origen visual
                fila_origen = int(i) + 2 if isinstance(i, (int,)) else int(i) + 2
                cruda = {
                    "fila_origen": fila_origen,
                    "fecha": None,
                    "cuenta": None,
                    "concepto": None,
                    "identidad": None,
                    "nombre_tercero": None,
                    "telefonos_tercero": None,
                    "credito": None,
                }
                for col_excel, destino in mapping.items():
                    cruda[destino] = _as_text(row.get(col_excel))

                # Saltar filas completamente vacías
                if not any(
                    cruda[k]
                    for k in (
                        "fecha",
                        "cuenta",
                        "concepto",
                        "identidad",
                        "nombre_tercero",
                        "credito",
                    )
                ):
                    continue
                filas.append(cruda)

            if not filas:
                return {
                    "success": False,
                    "message": "No se encontraron filas con datos en el archivo",
                    "data": None,
                }

            return {
                "success": True,
                "message": f"Leídas {len(filas)} filas del archivo",
                "data": {"filas": filas, "mapeo": mapping, "total": len(filas)},
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en VentasImportService.leer_archivo: {error_msg}")
            return {
                "success": False,
                "message": f"Error al leer el archivo: {error_msg}",
                "data": None,
            }

    @staticmethod
    def importar_raw(ruta_archivo: str) -> dict:
        """
        Lee el archivo Elisa y lo inserta en ventas_import_raw.

        - Conserva el dato original (columnas texto).
        - Calcula concepto_limpio / cantidad / descuento / atributos.
        - Calcula huella e idempotencia (Fase 5):
            * duplicado ya procesado → se guarda como omitido (no reprocessa)
            * duplicado fallido/pendiente → se inserta para reintentar
        - No marca procesado=true en filas nuevas (fases 2-4).
        - No toca productos, clientes, ventas ni movimientos.
        """
        print(f"--- Importando ventas Elisa (raw): {ruta_archivo} ---")
        try:
            leido = VentasImportService.leer_archivo(ruta_archivo)
            if not leido.get("success"):
                return leido

            filas = leido["data"]["filas"]
            lote_id = str(uuid.uuid4())
            valores = []
            insertadas = 0
            omitidas = 0
            reintentos = 0

            with get_cursor() as cur:
                for fila in filas:
                    parsed = parsear_fila_elisa(
                        fila.get("cuenta"), fila.get("concepto")
                    )
                    huella = calcular_huella_fila(
                        fecha=fila.get("fecha"),
                        cuenta=fila.get("cuenta"),
                        concepto=fila.get("concepto"),
                        identidad=fila.get("identidad"),
                        credito=fila.get("credito"),
                        fila_origen=fila.get("fila_origen"),
                    )

                    previa = _buscar_huella_previa(cur, huella)
                    es_duplicado_omitido = False
                    estado_resolucion = (
                        "no_aplica" if parsed["es_cuadre_caja"] else "pendiente"
                    )
                    estado_proceso = "pendiente"
                    procesado = False
                    venta_id_prev = None
                    error_proceso = None

                    if previa:
                        ya_ok = bool(previa.get("procesado")) or (
                            previa.get("estado_proceso") == "procesado"
                        )
                        if ya_ok:
                            # No volver a descontar stock ni crear venta.
                            es_duplicado_omitido = True
                            estado_proceso = "duplicado_omitido"
                            estado_resolucion = "no_aplica"
                            procesado = True  # no entra a colas de proceso
                            venta_id_prev = previa.get("venta_id")
                            omitidas += 1
                        else:
                            # Falló o quedó pendiente: permitir reintento.
                            reintentos += 1
                            error_proceso = None
                    else:
                        insertadas += 1

                    valores.append(
                        (
                            lote_id,
                            fila["fila_origen"],
                            fila.get("fecha"),
                            fila.get("cuenta"),
                            fila.get("concepto"),
                            fila.get("identidad"),
                            fila.get("nombre_tercero"),
                            fila.get("telefonos_tercero"),
                            fila.get("credito"),
                            parsed["concepto_limpio"],
                            parsed["cantidad"],
                            parsed["descuento_pct"],
                            Json(parsed["atributos"]),
                            parsed["es_cuadre_caja"],
                            procesado,
                            estado_resolucion,
                            estado_proceso,
                            huella,
                            es_duplicado_omitido,
                            venta_id_prev,
                            error_proceso,
                        )
                    )

                if valores:
                    execute_values(
                        cur,
                        """
                        INSERT INTO ventas_import_raw (
                            lote_id, fila_origen,
                            fecha, cuenta, concepto, identidad,
                            nombre_tercero, telefonos_tercero, credito,
                            concepto_limpio, cantidad, descuento_pct,
                            atributos, es_cuadre_caja, procesado,
                            estado_resolucion, estado_proceso,
                            huella, es_duplicado_omitido,
                            venta_id, error_proceso
                        ) VALUES %s
                        """,
                        valores,
                        page_size=200,
                    )

            resumen = VentasImportService.resumen_lote(lote_id)
            print(
                f" Lote {lote_id}: {len(valores)} filas "
                f"(nuevas={insertadas}, reintentos={reintentos}, "
                f"omitidas={omitidas})"
            )
            return {
                "success": True,
                "message": (
                    f"Importación raw: {insertadas} nuevas, "
                    f"{reintentos} reintento(s), "
                    f"{omitidas} duplicado(s) omitido(s)"
                ),
                "data": {
                    "lote_id": lote_id,
                    "filas_insertadas": len(valores),
                    "filas_nuevas": insertadas,
                    "filas_reintento": reintentos,
                    "filas_duplicado_omitido": omitidas,
                    "resumen": resumen.get("data"),
                },
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en VentasImportService.importar_raw: {error_msg}")
            return {
                "success": False,
                "message": f"Error al importar ventas: {error_msg}",
                "data": None,
            }

    @staticmethod
    def resumen_lote(lote_id: str) -> dict:
        """Resumen por cuenta/categoría de un lote importado."""
        try:
            filas = run_query(
                """
                SELECT cuenta,
                       COALESCE(atributos->>'categoria', 'desconocida') AS categoria,
                       COUNT(*) AS n,
                       SUM(CASE WHEN es_cuadre_caja THEN 1 ELSE 0 END) AS cuadres,
                       SUM(CASE WHEN procesado THEN 1 ELSE 0 END) AS procesados
                FROM ventas_import_raw
                WHERE lote_id = %s
                GROUP BY cuenta, COALESCE(atributos->>'categoria', 'desconocida')
                ORDER BY cuenta
                """,
                (lote_id,),
            )
            total = run_query(
                """
                SELECT COUNT(*) AS n,
                       SUM(CASE WHEN es_cuadre_caja THEN 1 ELSE 0 END) AS cuadres_caja,
                       SUM(CASE WHEN procesado THEN 1 ELSE 0 END) AS procesados
                FROM ventas_import_raw
                WHERE lote_id = %s
                """,
                (lote_id,),
                fetch_one=True,
            )
            return {
                "success": True,
                "message": "Resumen del lote",
                "data": {
                    "lote_id": lote_id,
                    "total": int(total["n"] or 0) if total else 0,
                    "cuadres_caja": int(total["cuadres_caja"] or 0) if total else 0,
                    "procesados": int(total["procesados"] or 0) if total else 0,
                    "por_cuenta": filas or [],
                },
            }
        except Exception as e:
            error_msg = str(e)
            return {
                "success": False,
                "message": f"Error al resumir lote: {error_msg}",
                "data": None,
            }

    @staticmethod
    def get_lote(lote_id: str, solo_pendientes: bool = False) -> dict:
        """Trae las filas raw de un lote (para fases siguientes o depuración)."""
        try:
            where = "WHERE lote_id = %s"
            params: list = [lote_id]
            if solo_pendientes:
                where += " AND procesado = false"
            data = run_query(
                f"""
                SELECT *
                FROM ventas_import_raw
                {where}
                ORDER BY fila_origen
                """,
                tuple(params),
            )
            return {
                "success": True,
                "message": f"{len(data or [])} filas del lote",
                "data": data or [],
            }
        except Exception as e:
            error_msg = str(e)
            return {
                "success": False,
                "message": f"Error al obtener lote: {error_msg}",
                "data": [],
            }
