"""
Servicio de Bitácora (auditoría).

Registra y consulta acciones sensibles del sistema en la tabla 'bitacora'.

Esquema real verificado (local y Supabase, idéntico):
    bitacora (
        id          uuid          DEFAULT gen_random_uuid(),
        usuario_id  uuid          NOT NULL,
        accion      text          NOT NULL,
        entidad     text          NULL,
        entidad_id  text          NULL,
        detalle     text          NULL,
        detalles    jsonb         NULL,   -- legado
        fecha       timestamptz   DEFAULT CURRENT_TIMESTAMP,
        dirty       boolean       DEFAULT true,
        synced_at   timestamptz
    )

La columna JSONB 'detalles' se conserva solo por compatibilidad con
registros antiguos; los registros nuevos usan las columnas
'entidad', 'entidad_id' y 'detalle'.


Qué se registra (catálogo cerrado ACCIONES_VALIDAS):
    LOGIN_FALLIDO, ELIMINACION, CAMBIO_ROL, ANULACION_VENTA,
    AJUSTE_STOCK, BAJA_STOCK, CAMBIO_PRECIO

Qué NO se registra:
    - Entradas/salidas normales de inventario (eso ya vive en 'movimientos').
    - Lecturas o consultas.
    - Ediciones rutinarias de campos no sensibles.
    - Snapshots completos antes/después — solo un 'detalle' de texto corto
      (máx. ~200 caracteres).

Mismo contrato que el resto de servicios:
  - Cada función usa try/except
  - Siempre retorna {'success': bool, 'message': str, 'data': ...}
  - SIN importaciones de Flet — solo lógica pura

Importante:
    El registro de bitácora NUNCA debe ser bloqueante. Si falla, se
    loguea el error pero no se propaga, para que la operación original
    no se vea afectada.

Pendiente (fuera de alcance de esta implementación):
    Instrumentar llamadas a registrar() desde productos_service,
    ventas_service, auth_service, etc. Cada punto de instrumentación
    debe ser su propio prompt scopeado.
"""

from datetime import date

from src.core.local_db import run_query


# Catálogo cerrado de acciones auditables.
ACCIONES_VALIDAS = [
    "LOGIN_FALLIDO",
    "ELIMINACION",
    "CAMBIO_ROL",
    "ANULACION_VENTA",
    "AJUSTE_STOCK",
    "BAJA_STOCK",
    "CAMBIO_PRECIO",
    "FUSION_PRODUCTO",
]

_MAX_DETALLE = 200


class BitacoraService:
    """Auditoría del sistema. Sin dependencias de Flet."""

    @staticmethod
    def get_all(
        usuario_id: str = None,
        accion: str = None,
        fecha_inicio: date = None,
        fecha_fin: date = None,
    ):
        """
        Trae el historial de bitácora, más reciente primero.

        Parámetros opcionales de filtro:
            usuario_id:   id del usuario que realizó la acción
            accion:       uno de ACCIONES_VALIDAS
            fecha_inicio: fecha mínima (date)
            fecha_fin:    fecha máxima (date)

        Retorna:
            dict: contrato estándar; 'data' es la lista de registros.
        """
        print("--- Trayendo bitácora ---")
        try:
            condiciones = []
            parametros = []

            if usuario_id:
                condiciones.append("b.usuario_id = %s")
                parametros.append(usuario_id)
            if accion:
                condiciones.append("b.accion = %s")
                parametros.append(accion)
            if fecha_inicio:
                condiciones.append("b.fecha::date >= %s")
                parametros.append(fecha_inicio)
            if fecha_fin:
                condiciones.append("b.fecha::date <= %s")
                parametros.append(fecha_fin)

            where = ""
            if condiciones:
                where = "WHERE " + " AND ".join(condiciones)

            data = run_query(
                f"""
                SELECT b.id,
                       b.usuario_id,
                       b.accion,
                       b.entidad,
                       b.entidad_id,
                       COALESCE(
                           b.detalle,
                           b.detalles->>'detalle',
                           b.detalles->>'descripcion'
                       ) AS detalle,
                       b.fecha,
                       u.name AS usuario,
                       u.rol
                FROM bitacora b
                LEFT JOIN usuarios u ON b.usuario_id = u.id
                {where}
                ORDER BY b.fecha DESC
                """,
                tuple(parametros) if parametros else (),
            )

            if not data:
                return {
                    "success": True,
                    "message": "No hay registros en la bitácora",
                    "data": [],
                }

            print(f" Se encontraron {len(data)} registro(s) en bitácora")
            return {
                "success": True,
                "message": "Bitácora obtenida",
                "data": data,
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en BitacoraService.get_all: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener bitácora: {error_msg}",
                "data": [],
            }

    @staticmethod
    def get_by_entidad(entidad: str, entidad_id: str):
        """
        Trae el historial de bitácora de un registro específico
        (ej. todos los cambios de un producto), más reciente primero.

        Parámetros:
            entidad:    nombre de la entidad, ej: "producto", "venta"
            entidad_id: id del registro afectado

        Retorna:
            dict: contrato estándar; 'data' es la lista de registros.
        """
        print(f"--- Trayendo bitácora de {entidad} {entidad_id} ---")
        try:
            data = run_query(
                """
                SELECT b.id,
                       b.usuario_id,
                       b.accion,
                       b.entidad,
                       b.entidad_id,
                       COALESCE(
                           b.detalle,
                           b.detalles->>'detalle',
                           b.detalles->>'descripcion'
                       ) AS detalle,
                       b.fecha,
                       u.name AS usuario,
                       u.rol
                FROM bitacora b
                LEFT JOIN usuarios u ON b.usuario_id = u.id
                WHERE b.entidad = %s
                  AND b.entidad_id = %s
                ORDER BY b.fecha DESC
                """,
                (entidad, str(entidad_id)),
            )

            if not data:
                return {
                    "success": True,
                    "message": "No hay registros para esa entidad",
                    "data": [],
                }

            return {
                "success": True,
                "message": "Bitácora de la entidad obtenida",
                "data": data,
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en BitacoraService.get_by_entidad: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener bitácora: {error_msg}",
                "data": [],
            }

    @staticmethod
    def registrar(
        usuario_id: str,
        accion: str,
        entidad: str = None,
        entidad_id: str = None,
        detalle: str = None,
    ):
        """
        Inserta un nuevo registro de auditoría.

        Parámetros:
            usuario_id: id de la tabla 'usuarios' de quien realiza la
                        acción. Debe recibirse como parámetro — este
                        servicio no lo inventa ni lo asume.
            accion:     debe estar dentro de ACCIONES_VALIDAS.
            entidad:    nombre de la entidad afectada, ej: "producto".
            entidad_id: id del registro afectado (opcional).
            detalle:    texto corto (se trunca a ~200 caracteres).

        Retorna:
            dict: contrato estándar; 'data' contiene el registro insertado.

        Nota:
            Nunca lanza excepción hacia el llamador: un fallo aquí no
            debe afectar la operación auditada.
        """
        print(f"--- Registrando en bitácora: {accion} ---")
        try:
            if accion not in ACCIONES_VALIDAS:
                print(f" Acción no auditable, se omite: {accion}")
                return {
                    "success": False,
                    "message": (
                        f"Acción '{accion}' no está en el catálogo "
                        "de acciones auditables"
                    ),
                }

            detalle_corto = (detalle or "")[:_MAX_DETALLE]

            registro = run_query(
                """
                INSERT INTO bitacora
                    (usuario_id, accion, entidad, entidad_id, detalle)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    usuario_id,
                    accion,
                    entidad,
                    str(entidad_id) if entidad_id else None,
                    detalle_corto,
                ),
                fetch_one=True,
            )

            if not registro:
                return {
                    "success": False,
                    "message": "No se pudo registrar la bitácora",
                }

            print(f" Bitácora registrada: {accion}")
            return {
                "success": True,
                "message": "Bitácora registrada",
                "data": registro,
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en BitacoraService.registrar: {error_msg}")
            return {
                "success": False,
                "message": f"Error al registrar bitácora: {error_msg}",
            }
