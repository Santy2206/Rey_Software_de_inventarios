"""
Servicio de Bitácora.

Registra y consulta las acciones de los usuarios en la tabla 'bitacora'.
Es una tabla de auditoría: cada operación relevante (login, CRUD, ventas,
movimientos) debería dejar un registro aquí.

Tabla:
    bitacora (id, usuario_id, accion, detalles, fecha)

    - detalles es de tipo JSONB; se inserta usando psycopg2.extras.Json.
    - fecha tiene DEFAULT CURRENT_TIMESTAMP.

Mismo contrato que el resto de servicios:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - Si hay datos, los incluye bajo la llave 'data'
  - SIN importaciones de Flet — solo lógica pura

Importante:
    El registro de bitácora NUNCA debe ser bloqueante. Si falla, se
    loguea el error pero no se propaga, para que la operación original
    (venta, movimiento, etc.) no se vea afectada.
"""

from datetime import date

from psycopg2.extras import Json

from src.core.local_db import run_query


class BitacoraService:

    @staticmethod
    def get_all(
        usuario_id: str = None,
        accion: str = None,
        fecha_inicio: date = None,
        fecha_fin: date = None,
    ):
        """
        Trae los registros de bitácora, opcionalmente filtrados.

        Parámetros:
            usuario_id:  id del usuario que realizó la acción
            accion:      tipo de acción, ej: "LOGIN", "BODEGA", "VENTA"
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
                SELECT b.*,
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
    def registrar(usuario_id: str, accion: str, detalle: dict):
        """
        Inserta un nuevo registro en la bitácora.

        Parámetros:
            usuario_id: id del usuario que realiza la acción
            accion:     etiqueta corta, ej: "LOGIN", "BODEGA", "PRODUCTO"
            detalle:    diccionario con información adicional (descripción,
                        ids afectados, etc.)

        Retorna:
            dict: contrato estándar; 'data' contiene el registro insertado.
        """
        print(f"--- Registrando en bitácora: {accion} ---")
        try:
            detalle_db = Json(detalle) if detalle is not None else None

            registro = run_query(
                """
                INSERT INTO bitacora (usuario_id, accion, detalles)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (usuario_id, accion, detalle_db),
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
