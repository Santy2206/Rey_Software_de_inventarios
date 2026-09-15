"""
Capa de sincronización local ↔ nube.

Responsabilidades:
    - Detectar cambios locales pendientes de sincronizar (dirty = true).
    - Enviar registros locales a Supabase mediante upsert.
    - Marcar registros sincronizados (dirty = false, synced_at = now()).
    - Fallar de forma segura: si no hay conexión, deja los registros
      dirty para un reintento futuro.

Reglas:
    - Funciona de forma independiente a la interfaz.
    - SIN importaciones de Flet.
    - Debe operar sin conexión a internet de forma segura
      (fallo gracioso y lógica de reintento).

Estrategia de reintento:
    - Cada fila se intenta individualmente; si falla, se mantiene
      dirty = true y se registra el error en consola.
    - sync_pendientes se puede ejecutar manualmente desde la UI o
      periódicamente en segundo plano. Por defecto se recomienda
      disparo manual o periódico desde dashboard para evitar
      consumo de red innecesario.
"""

import queue
import threading
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from src.core.local_db import get_cursor, run_query
from src.core.supabase_client import supabase

# Máximo de segundos que puede tardar un upsert individual a Supabase.
# Si se supera, la fila se marca como fallida y el sync continúa:
# evita que un request colgado deje el diálogo de progreso "bugueado".
_UPSERT_TIMEOUT_SEGUNDOS = 60


def _upsert_con_timeout(payload: dict, tabla: str):
    """
    Ejecuta supabase.table(tabla).upsert(payload) con timeout duro.

    Retorna el objeto respuesta de Supabase.
    Lanza TimeoutError si el request no responde en el límite.
    """
    cola: queue.Queue = queue.Queue(maxsize=1)

    def _llamar():
        try:
            resp = supabase.table(tabla).upsert(payload).execute()
            cola.put(("ok", resp))
        except Exception as e:  # noqa: BLE001
            cola.put(("error", e))

    threading.Thread(target=_llamar, daemon=True).start()
    try:
        estado, valor = cola.get(timeout=_UPSERT_TIMEOUT_SEGUNDOS)
    except queue.Empty:
        raise TimeoutError(
            f"Upsert a '{tabla}' no respondió en "
            f"{_UPSERT_TIMEOUT_SEGUNDOS}s (conexión con Supabase?)"
        )
    if estado == "error":
        raise valor
    return valor


# Orden de sincronización respetando FKs (padres primero).
# usuarios no tiene dirty/synced_at: se sincroniza siempre como base.
_TABLAS_BASE = [
    "usuarios",  # sin dirty: siempre se sube para satisfacer FKs
]

_TABLAS_A_SYNC = [
    "bodegas",
    "clientes",
    "productos",
    "movimientos",
    "ventas",
    "venta_detalle",
    "bitacora",
]

# Columnas de control que no deben enviarse a Supabase.
_COLUMNAS_CONTROL = {"dirty", "synced_at"}

# Columnas permitidas por tabla en Supabase. Si una tabla no aparece aquí,
# se envían todas las columnas menos las de control.
_COLUMNAS_PERMITIDAS = {
}


def _serializar_valor(valor):
    """Convierte tipos de PostgreSQL en valores serializables por Supabase."""
    if valor is None:
        return None
    if isinstance(valor, UUID):
        return str(valor)
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, dict):
        return {k: _serializar_valor(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_serializar_valor(v) for v in valor]
    return valor


def _preparar_fila(fila: dict, tabla: str) -> dict:
    """Convierte una fila RealDictCursor en un dict listo para upsert."""
    permitidas = _COLUMNAS_PERMITIDAS.get(tabla)
    return {
        k: _serializar_valor(v)
        for k, v in fila.items()
        if k not in _COLUMNAS_CONTROL and (permitidas is None or k in permitidas)
    }


class SyncService:
    """
    Servicio de sincronización local-first.

    No depende de Flet. Puede ejecutarse manualmente o en un thread
    de fondo disparado por la UI.
    """

    @staticmethod
    def _tabla_tiene_dirty(tabla: str) -> bool:
        """True si la tabla tiene columna dirty (no aplica a usuarios)."""
        fila = run_query(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = 'dirty'
            LIMIT 1
            """,
            (tabla,),
            fetch_one=True,
        )
        return bool(fila)

    @staticmethod
    def pendientes_por_tabla() -> dict:
        """
        Retorna un conteo de filas dirty pendientes por tabla.

        Retorna:
            dict: contrato estándar {'success', 'message', 'data'}
        """
        print("--- Consultando pendientes de sincronización ---")
        try:
            resumen = {}
            for tabla in _TABLAS_A_SYNC:
                if not SyncService._tabla_tiene_dirty(tabla):
                    resumen[tabla] = 0
                    continue
                fila = run_query(
                    f"SELECT COUNT(*) AS n FROM {tabla} WHERE dirty = true",
                    fetch_one=True,
                )
                resumen[tabla] = fila["n"] if fila else 0

            total = sum(resumen.values())
            return {
                "success": True,
                "message": f"{total} registros pendientes de sincronizar",
                "data": resumen,
            }
        except Exception as e:
            error_msg = str(e)
            print(f" Error en SyncService.pendientes_por_tabla: {error_msg}")
            return {
                "success": False,
                "message": f"Error al consultar pendientes: {error_msg}",
                "data": {},
            }

    @staticmethod
    def _contar_filas(tabla: str, solo_dirty: bool) -> int:
        """Cuenta las filas que se van a subir de una tabla."""
        try:
            tiene_dirty = SyncService._tabla_tiene_dirty(tabla)
            if solo_dirty and tiene_dirty:
                fila = run_query(
                    f"SELECT COUNT(*) AS n FROM {tabla} WHERE dirty = true",
                    fetch_one=True,
                )
            else:
                fila = run_query(
                    f"SELECT COUNT(*) AS n FROM {tabla}",
                    fetch_one=True,
                )
            return fila["n"] if fila else 0
        except Exception:
            return 0

    @staticmethod
    def _upsert_tabla(
        tabla: str, solo_dirty: bool = True, on_row=None
    ) -> dict:
        """
        Sube filas de una tabla a Supabase.

        Si solo_dirty=True, solo filas dirty.
        Si la tabla no tiene dirty, sube todas (caso usuarios).

        on_row: callback opcional llamado tras procesar cada fila con la
        tabla como argumento.
        """
        tiene_dirty = SyncService._tabla_tiene_dirty(tabla)
        try:
            if solo_dirty and tiene_dirty:
                filas = run_query(f"SELECT * FROM {tabla} WHERE dirty = true ORDER BY id")
            else:
                filas = run_query(f"SELECT * FROM {tabla} ORDER BY id")
        except Exception as e:
            error_msg = str(e)
            print(f"   No se pudo leer {tabla}: {error_msg}")
            return {"subidos": 0, "fallidos": 0, "error": error_msg}

        if not filas:
            return {"subidos": 0, "fallidos": 0, "error": None}

        subidos = 0
        fallidos = 0
        primer_error = None
        for fila in filas:
            fila_id = fila.get("id")
            try:
                payload = _preparar_fila(fila, tabla)
                resp = _upsert_con_timeout(payload, tabla)

                if resp is None or not getattr(resp, "data", None):
                    raise Exception(f"Respuesta inesperada de Supabase: {resp}")

                if tiene_dirty:
                    run_query(
                        f"""
                        UPDATE {tabla}
                        SET dirty = false,
                            synced_at = now()
                        WHERE id = %s
                        """,
                        (fila_id,),
                    )
                subidos += 1
            except Exception as e:
                error_msg = str(e)
                if primer_error is None:
                    primer_error = error_msg
                print(f"   Fallo al sincronizar {tabla} id={fila_id}: {error_msg}")
                fallidos += 1
            finally:
                if on_row:
                    try:
                        on_row(tabla)
                    except Exception:
                        pass

        return {"subidos": subidos, "fallidos": fallidos, "error": primer_error}

    @staticmethod
    def sync_pendientes(on_progress=None):
        """
        Sube a Supabase todas las filas dirty de las tablas configuradas.

        Parámetros:
            on_progress: callback opcional llamado por cada fila procesada
                         con (enviados, total, tabla).

        Orden:
            1. tablas base (usuarios) para satisfacer FKs
            2. resto en orden de dependencias (bodegas -> ... -> bitacora)

        Retorna:
            dict: contrato estándar con resumen de subidos/fallidos.
        """
        print("--- Iniciando sincronización con Supabase ---")
        resumen = {}
        total_subidos = 0
        total_fallidos = 0

        try:
            # Total de filas a procesar (para progreso)
            total = 0
            for tabla in _TABLAS_BASE:
                total += SyncService._contar_filas(tabla, solo_dirty=False)
            for tabla in _TABLAS_A_SYNC:
                total += SyncService._contar_filas(tabla, solo_dirty=True)

            enviados = 0

            def _on_row(tabla):
                nonlocal enviados
                enviados += 1
                if on_progress:
                    try:
                        on_progress(enviados, total, tabla)
                    except Exception:
                        pass

            # 1) Bases (siempre, para que existan en la nube)
            for tabla in _TABLAS_BASE:
                print(f" Sincronizando tabla base: {tabla}")
                r = SyncService._upsert_tabla(
                    tabla, solo_dirty=False, on_row=_on_row
                )
                resumen[tabla] = r
                total_subidos += r["subidos"]
                total_fallidos += r["fallidos"]

            # 2) Tablas con dirty en orden de FKs
            for tabla in _TABLAS_A_SYNC:
                print(f" Sincronizando tabla: {tabla}")
                r = SyncService._upsert_tabla(
                    tabla, solo_dirty=True, on_row=_on_row
                )
                resumen[tabla] = r
                total_subidos += r["subidos"]
                total_fallidos += r["fallidos"]

            mensaje = (
                f"Sincronización completada: {total_subidos} subidos, "
                f"{total_fallidos} fallidos"
            )
            if total_fallidos > 0:
                errores = []
                for tabla, r in resumen.items():
                    if r.get("fallidos") and r.get("error"):
                        errores.append(f"{tabla}: {r['error'][:100]}")
                if errores:
                    mensaje += ". Errores: " + " | ".join(errores[:3])

            return {
                "success": total_fallidos == 0,
                "message": mensaje,
                "data": resumen,
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error crítico en SyncService.sync_pendientes: {error_msg}")
            print(traceback.format_exc())
            return {
                "success": False,
                "message": f"Sincronización interrumpida: {error_msg}",
                "data": resumen,
            }

    @staticmethod
    def sync_pendientes_background(callback=None, on_progress=None):
        """
        Ejecuta sync_pendientes en un hilo de fondo.

        Parámetros:
            callback: función opcional que recibe el resultado del sync.
            on_progress: función opcional llamada por cada fila procesada
                         con (enviados, total, tabla).

        Retorna:
            threading.Thread: el hilo iniciado.
        """
        import threading

        def _worker():
            resultado = SyncService.sync_pendientes(on_progress=on_progress)
            if callback:
                callback(resultado)
            return resultado

        hilo = threading.Thread(target=_worker, daemon=True)
        hilo.start()
        return hilo
