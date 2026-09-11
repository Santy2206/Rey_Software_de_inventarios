"""
Resolución de clientes Elisa (Fase 3).

Toma IDENTIDAD / NOMBRE DEL TERCERO / TELEFONOS DEL TERCERO de
ventas_import_raw y:

  1. Separa prefijo numérico Elisa del nombre (codigo_elisa + nombre_limpio).
  2. Resuelve la cédula 222222222 al cliente genérico fijo (es_generico=true).
  3. Hace upsert por cédula sin sobrescribir datos buenos con vacíos.
  4. Si el nombre nuevo es muy distinto al existente (pg_trgm), deja la fila
     en conflicto para revisión manual.
  5. Escribe cliente_id + estado_cliente en ventas_import_raw.

NO genera movimientos ni toca stock.
SIN imports de Flet.
"""

from __future__ import annotations

import re

from psycopg2.extras import Json

from src.core.local_db import run_query


# Cédula del cliente genérico de mostrador (Elisa: CUANTIAS MENORES).
CEDULA_GENERICO = "222222222"
NOMBRE_GENERICO = "CUANTIAS MENORES"

# Si similarity(nombre_existente, nombre_nuevo) < este umbral → conflicto.
UMBRAL_NOMBRE_MISMO_CLIENTE = 0.35

_RE_PREFIJO = re.compile(r"^\s*(\d+)\s+(.+)$")
_RE_SOLO_DIGITOS = re.compile(r"\D+")


def normalizar_cedula(identidad: str | None) -> str | None:
    """Deja solo dígitos de la cédula. None si queda vacío."""
    if identidad is None:
        return None
    digitos = _RE_SOLO_DIGITOS.sub("", str(identidad))
    return digitos or None


def separar_nombre_tercero(nombre_tercero: str | None) -> dict:
    """
    Separa '1307 CARMONA LILIANA' → codigo_elisa='1307', nombre_limpio='CARMONA LILIANA'.
    Sin prefijo numérico → codigo_elisa=None.
    """
    crudo = "" if nombre_tercero is None else str(nombre_tercero).strip()
    if not crudo:
        return {"codigo_elisa": None, "nombre_limpio": None, "nombre_original": crudo or None}

    m = _RE_PREFIJO.match(crudo)
    if m:
        codigo = m.group(1)
        resto = m.group(2).strip()
        # Evitar tratar cédulas genéricas mal pegadas como prefijo solo
        return {
            "codigo_elisa": codigo,
            "nombre_limpio": resto or None,
            "nombre_original": crudo,
        }

    return {
        "codigo_elisa": None,
        "nombre_limpio": crudo,
        "nombre_original": crudo,
    }


def _limpio_o_none(valor: str | None) -> str | None:
    if valor is None:
        return None
    t = str(valor).strip()
    return t or None


def _similitud_nombres(a: str | None, b: str | None) -> float | None:
    if not a or not b:
        return None
    fila = run_query(
        "SELECT similarity(UPPER(%s), UPPER(%s)) AS s",
        (a, b),
        fetch_one=True,
    )
    if not fila or fila.get("s") is None:
        return None
    return float(fila["s"])


class ClientesResolucionService:
    """Upsert y cola de conflictos de clientes Elisa."""

    @staticmethod
    def asegurar_cliente_generico() -> dict:
        """Crea (una sola vez) el cliente genérico 222222222 / CUANTIAS MENORES."""
        try:
            existente = run_query(
                "SELECT * FROM clientes WHERE cedula = %s OR es_generico = true LIMIT 1",
                (CEDULA_GENERICO,),
                fetch_one=True,
            )
            if existente:
                # Garantizar flags
                if (
                    existente.get("cedula") != CEDULA_GENERICO
                    or not existente.get("es_generico")
                ):
                    existente = run_query(
                        """
                        UPDATE clientes
                        SET cedula = %s,
                            es_generico = true,
                            nombre = COALESCE(NULLIF(nombre, ''), %s),
                            dirty = true
                        WHERE id = %s
                        RETURNING *
                        """,
                        (CEDULA_GENERICO, NOMBRE_GENERICO, existente["id"]),
                        fetch_one=True,
                    )
                return {
                    "success": True,
                    "message": "Cliente genérico listo",
                    "data": existente,
                }

            creado = run_query(
                """
                INSERT INTO clientes (nombre, cedula, es_generico, dirty)
                VALUES (%s, %s, true, true)
                RETURNING *
                """,
                (NOMBRE_GENERICO, CEDULA_GENERICO),
                fetch_one=True,
            )
            return {
                "success": True,
                "message": "Cliente genérico creado",
                "data": creado,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al asegurar cliente genérico: {e}",
                "data": None,
            }

    @staticmethod
    def _buscar_por_cedula(cedula: str):
        return run_query(
            "SELECT * FROM clientes WHERE cedula = %s LIMIT 1",
            (cedula,),
            fetch_one=True,
        )

    @staticmethod
    def _crear_cliente(
        nombre: str,
        cedula: str | None,
        telefono: str | None,
        codigo_elisa: str | None,
        es_generico: bool = False,
    ):
        return run_query(
            """
            INSERT INTO clientes
                (nombre, telefono, cedula, codigo_elisa, es_generico, dirty)
            VALUES (%s, %s, %s, %s, %s, true)
            RETURNING *
            """,
            (nombre, telefono, cedula, codigo_elisa, es_generico),
            fetch_one=True,
        )

    @staticmethod
    def _actualizar_si_vacio(
        cliente: dict,
        nombre_nuevo: str | None,
        telefono_nuevo: str | None,
        codigo_elisa_nuevo: str | None,
        forzar_nombre: bool = False,
    ):
        """
        Actualiza solo campos donde el valor nuevo no viene vacío.
        Si forzar_nombre=False y hay conflicto de nombres, no cambia el nombre.
        """
        sets = []
        params = []

        if telefono_nuevo:
            actual = _limpio_o_none(cliente.get("telefono"))
            if not actual or actual != telefono_nuevo:
                sets.append("telefono = %s")
                params.append(telefono_nuevo)

        if codigo_elisa_nuevo:
            actual = _limpio_o_none(cliente.get("codigo_elisa"))
            if not actual:
                sets.append("codigo_elisa = %s")
                params.append(codigo_elisa_nuevo)

        if nombre_nuevo and forzar_nombre:
            sets.append("nombre = %s")
            params.append(nombre_nuevo)
        elif nombre_nuevo:
            actual = _limpio_o_none(cliente.get("nombre"))
            if not actual:
                sets.append("nombre = %s")
                params.append(nombre_nuevo)

        if not sets:
            return cliente

        sets.append("dirty = true")
        params.append(cliente["id"])
        return run_query(
            f"""
            UPDATE clientes
            SET {', '.join(sets)}
            WHERE id = %s
            RETURNING *
            """,
            tuple(params),
            fetch_one=True,
        )

    @staticmethod
    def resolver_uno(
        identidad: str | None,
        nombre_tercero: str | None,
        telefonos_tercero: str | None,
        umbral_nombre: float = UMBRAL_NOMBRE_MISMO_CLIENTE,
    ) -> dict:
        """
        Resuelve un cliente a partir de los campos crudos de Elisa.

        Retorna:
          {
            success, message, data: {
              cliente_id, estado_cliente, codigo_elisa, nombre_limpio,
              conflicto (dict|None), cliente
            }
          }
        """
        try:
            cedula = normalizar_cedula(identidad)
            partes = separar_nombre_tercero(nombre_tercero)
            nombre_limpio = partes["nombre_limpio"]
            codigo_elisa = partes["codigo_elisa"]
            telefono = _limpio_o_none(telefonos_tercero)

            # --- genérico ---
            if cedula == CEDULA_GENERICO or (
                nombre_limpio
                and nombre_limpio.upper() == NOMBRE_GENERICO
                and (cedula is None or cedula == CEDULA_GENERICO)
            ):
                gen = ClientesResolucionService.asegurar_cliente_generico()
                if not gen.get("success"):
                    return gen
                cliente = gen["data"]
                return {
                    "success": True,
                    "message": "Cliente genérico",
                    "data": {
                        "cliente_id": str(cliente["id"]),
                        "estado_cliente": "vinculado",
                        "codigo_elisa": None,
                        "nombre_limpio": NOMBRE_GENERICO,
                        "conflicto": None,
                        "cliente": cliente,
                    },
                }

            if not cedula:
                return {
                    "success": True,
                    "message": "Sin cédula: requiere revisión",
                    "data": {
                        "cliente_id": None,
                        "estado_cliente": "conflicto",
                        "codigo_elisa": codigo_elisa,
                        "nombre_limpio": nombre_limpio,
                        "conflicto": {
                            "motivo": "sin_cedula",
                            "identidad": identidad,
                            "nombre_tercero": nombre_tercero,
                        },
                        "cliente": None,
                    },
                }

            existente = ClientesResolucionService._buscar_por_cedula(cedula)
            if not existente:
                # El nombre conserva el prefijo DDMM de cumpleaños
                # (ej. "1704 DIAZ SANTIAGO") como en el archivo Elisa.
                nombre_guardar = (
                    partes["nombre_original"] or nombre_limpio
                )
                if not nombre_guardar:
                    nombre_guardar = f"CLIENTE {cedula}"
                cliente = ClientesResolucionService._crear_cliente(
                    nombre=nombre_guardar,
                    cedula=cedula,
                    telefono=telefono,
                    codigo_elisa=codigo_elisa,
                )
                return {
                    "success": True,
                    "message": "Cliente creado",
                    "data": {
                        "cliente_id": str(cliente["id"]),
                        "estado_cliente": "creado",
                        "codigo_elisa": codigo_elisa,
                        "nombre_limpio": nombre_limpio,
                        "conflicto": None,
                        "cliente": cliente,
                    },
                }

            # Existe: detectar conflicto de nombre
            nombre_actual = _limpio_o_none(existente.get("nombre"))
            conflicto = None
            forzar_nombre = False
            if nombre_limpio and nombre_actual:
                sim = _similitud_nombres(nombre_actual, nombre_limpio)
                if sim is not None and sim < umbral_nombre:
                    conflicto = {
                        "motivo": "nombre_distinto",
                        "similitud": sim,
                        "nombre_existente": nombre_actual,
                        "nombre_nuevo": nombre_limpio,
                        "cedula": cedula,
                        "cliente_id_sugerido": str(existente["id"]),
                    }

            # Actualizar teléfono / codigo_elisa sin pisar con vacío;
            # nombre solo si no hay conflicto
            cliente = ClientesResolucionService._actualizar_si_vacio(
                existente,
                nombre_nuevo=nombre_limpio,
                telefono_nuevo=telefono,
                codigo_elisa_nuevo=codigo_elisa,
                forzar_nombre=forzar_nombre,
            )

            if conflicto:
                return {
                    "success": True,
                    "message": "Conflicto de nombre: requiere revisión",
                    "data": {
                        "cliente_id": None,
                        "estado_cliente": "conflicto",
                        "codigo_elisa": codigo_elisa,
                        "nombre_limpio": nombre_limpio,
                        "conflicto": conflicto,
                        "cliente": cliente or existente,
                    },
                }

            return {
                "success": True,
                "message": "Cliente vinculado",
                "data": {
                    "cliente_id": str((cliente or existente)["id"]),
                    "estado_cliente": "vinculado",
                    "codigo_elisa": codigo_elisa,
                    "nombre_limpio": nombre_limpio or nombre_actual,
                    "conflicto": None,
                    "cliente": cliente or existente,
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al resolver cliente: {e}",
                "data": None,
            }

    @staticmethod
    def resolver_lote(lote_id: str, umbral_nombre: float = UMBRAL_NOMBRE_MISMO_CLIENTE) -> dict:
        """
        Resuelve clientes de todas las filas de un lote.
        No marca procesado=true ni toca stock.
        """
        print(f"--- Resolviendo clientes del lote {lote_id} ---")
        try:
            filas = run_query(
                """
                SELECT id, identidad, nombre_tercero, telefonos_tercero,
                       estado_cliente
                FROM ventas_import_raw
                WHERE lote_id = %s
                  AND COALESCE(es_duplicado_omitido, false) = false
                  AND estado_cliente IN ('pendiente', 'conflicto')
                ORDER BY fila_origen
                """,
                (lote_id,),
            )
            if not filas:
                return {
                    "success": True,
                    "message": "No hay filas de cliente pendientes en el lote",
                    "data": {
                        "lote_id": lote_id,
                        "vinculados": 0,
                        "creados": 0,
                        "conflictos": 0,
                    },
                }

            creados = 0

            # Asegurar genérico una vez por lote
            ClientesResolucionService.asegurar_cliente_generico()

            for fila in filas:
                r = ClientesResolucionService.resolver_uno(
                    identidad=fila.get("identidad"),
                    nombre_tercero=fila.get("nombre_tercero"),
                    telefonos_tercero=fila.get("telefonos_tercero"),
                    umbral_nombre=umbral_nombre,
                )
                if not r.get("success"):
                    run_query(
                        """
                        UPDATE ventas_import_raw
                        SET estado_cliente = 'conflicto',
                            conflicto_cliente = %s
                        WHERE id = %s
                        """,
                        (
                            Json({"motivo": "error", "detalle": r.get("message")}),
                            fila["id"],
                        ),
                    )
                    continue

                data = r["data"]
                if data["estado_cliente"] == "creado":
                    creados += 1
                estado_fila = (
                    "vinculado"
                    if data["estado_cliente"] in ("vinculado", "creado")
                    else data["estado_cliente"]
                )

                run_query(
                    """
                    UPDATE ventas_import_raw
                    SET cliente_id = %s,
                        estado_cliente = %s,
                        codigo_elisa = %s,
                        nombre_cliente_limpio = %s,
                        conflicto_cliente = %s
                    WHERE id = %s
                    """,
                    (
                        data.get("cliente_id"),
                        estado_fila,
                        data.get("codigo_elisa"),
                        data.get("nombre_limpio"),
                        Json(data["conflicto"]) if data.get("conflicto") else None,
                        fila["id"],
                    ),
                )

            resumen_q = run_query(
                """
                SELECT
                  COUNT(*) FILTER (WHERE estado_cliente = 'vinculado') AS vinculados,
                  COUNT(*) FILTER (WHERE estado_cliente = 'conflicto') AS conflictos
                FROM ventas_import_raw
                WHERE lote_id = %s
                """,
                (lote_id,),
                fetch_one=True,
            )
            resumen = {
                "lote_id": lote_id,
                "vinculados": int(resumen_q["vinculados"] or 0) if resumen_q else 0,
                "creados": creados,
                "conflictos": int(resumen_q["conflictos"] or 0) if resumen_q else 0,
            }
            print(f" Clientes lote: {resumen}")
            return {
                "success": True,
                "message": (
                    f"Clientes: {resumen['vinculados']} vinculados, "
                    f"{resumen['creados']} creados, "
                    f"{resumen['conflictos']} conflictos"
                ),
                "data": resumen,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al resolver clientes del lote: {e}",
                "data": None,
            }

    @staticmethod
    def resolver_pendientes(umbral_nombre: float = UMBRAL_NOMBRE_MISMO_CLIENTE) -> dict:
        try:
            lotes = run_query(
                """
                SELECT DISTINCT lote_id
                FROM ventas_import_raw
                WHERE estado_cliente IN ('pendiente', 'conflicto')
                  AND COALESCE(es_duplicado_omitido, false) = false
                """
            )
            if not lotes:
                return {
                    "success": True,
                    "message": "No hay clientes pendientes",
                    "data": {"lotes": 0},
                }
            detalle = []
            for row in lotes:
                r = ClientesResolucionService.resolver_lote(
                    str(row["lote_id"]), umbral_nombre
                )
                detalle.append(r.get("data"))
            return {
                "success": True,
                "message": f"Procesados {len(lotes)} lote(s) de clientes",
                "data": {"lotes": len(lotes), "detalle": detalle},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al resolver clientes pendientes: {e}",
                "data": None,
            }

    @staticmethod
    def get_conflictos(lote_id: str | None = None, limite: int = 200) -> dict:
        try:
            params: list = []
            where = "WHERE r.estado_cliente = 'conflicto'"
            if lote_id:
                where += " AND r.lote_id = %s"
                params.append(lote_id)
            params.append(limite)
            data = run_query(
                f"""
                SELECT r.*,
                       c.nombre AS cliente_sugerido_nombre,
                       c.cedula AS cliente_sugerido_cedula
                FROM ventas_import_raw r
                LEFT JOIN clientes c
                  ON c.id = NULLIF(r.conflicto_cliente->>'cliente_id_sugerido', '')::uuid
                {where}
                ORDER BY r.creado_en DESC, r.fila_origen
                LIMIT %s
                """,
                tuple(params),
            )
            return {
                "success": True,
                "message": f"{len(data or [])} conflicto(s)",
                "data": data or [],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al listar conflictos: {e}",
                "data": [],
            }

    @staticmethod
    def aceptar_cliente_existente(fila_id: str) -> dict:
        """
        En un conflicto de nombre: aceptar el cliente ya existente
        (no cambia su nombre) y vincular la fila.
        """
        try:
            fila = run_query(
                "SELECT * FROM ventas_import_raw WHERE id = %s",
                (fila_id,),
                fetch_one=True,
            )
            if not fila:
                return {"success": False, "message": "Fila no encontrada"}
            conf = fila.get("conflicto_cliente") or {}
            if not isinstance(conf, dict):
                conf = {}
            sugerido = conf.get("cliente_id_sugerido")
            if not sugerido:
                # fallback por cédula
                cedula = normalizar_cedula(fila.get("identidad"))
                if not cedula:
                    return {
                        "success": False,
                        "message": "No hay cliente sugerido en el conflicto",
                    }
                cli = ClientesResolucionService._buscar_por_cedula(cedula)
                if not cli:
                    return {"success": False, "message": "Cliente no encontrado"}
                sugerido = str(cli["id"])

            # actualizar teléfono/codigo si vienen con valor
            partes = separar_nombre_tercero(fila.get("nombre_tercero"))
            telefono = _limpio_o_none(fila.get("telefonos_tercero"))
            cli = run_query(
                "SELECT * FROM clientes WHERE id = %s",
                (sugerido,),
                fetch_one=True,
            )
            if cli:
                ClientesResolucionService._actualizar_si_vacio(
                    cli,
                    nombre_nuevo=None,
                    telefono_nuevo=telefono,
                    codigo_elisa_nuevo=partes.get("codigo_elisa"),
                    forzar_nombre=False,
                )

            actualizado = run_query(
                """
                UPDATE ventas_import_raw
                SET cliente_id = %s,
                    estado_cliente = 'vinculado',
                    codigo_elisa = COALESCE(codigo_elisa, %s),
                    nombre_cliente_limpio = COALESCE(
                        nombre_cliente_limpio, %s
                    ),
                    conflicto_cliente = NULL
                WHERE id = %s
                RETURNING *
                """,
                (
                    sugerido,
                    partes.get("codigo_elisa"),
                    partes.get("nombre_limpio"),
                    fila_id,
                ),
                fetch_one=True,
            )
            return {
                "success": True,
                "message": "Conflicto resuelto: se mantiene el cliente existente",
                "data": actualizado,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al aceptar cliente existente: {e}",
            }

    @staticmethod
    def actualizar_nombre_y_vincular(fila_id: str, nuevo_nombre: str | None = None) -> dict:
        """
        En un conflicto: sobrescribir el nombre del cliente existente con el
        del archivo (o el pasado explícitamente) y vincular.
        """
        try:
            fila = run_query(
                "SELECT * FROM ventas_import_raw WHERE id = %s",
                (fila_id,),
                fetch_one=True,
            )
            if not fila:
                return {"success": False, "message": "Fila no encontrada"}

            conf = fila.get("conflicto_cliente") or {}
            if not isinstance(conf, dict):
                conf = {}
            partes = separar_nombre_tercero(fila.get("nombre_tercero"))
            nombre = (nuevo_nombre or conf.get("nombre_nuevo") or partes.get("nombre_limpio") or "").strip()
            if not nombre:
                return {"success": False, "message": "Nombre vacío"}

            sugerido = conf.get("cliente_id_sugerido")
            cedula = normalizar_cedula(fila.get("identidad"))
            if not sugerido and cedula:
                cli = ClientesResolucionService._buscar_por_cedula(cedula)
                sugerido = str(cli["id"]) if cli else None
            if not sugerido:
                return {"success": False, "message": "No hay cliente a actualizar"}

            telefono = _limpio_o_none(fila.get("telefonos_tercero"))
            cli = run_query(
                """
                UPDATE clientes
                SET nombre = %s,
                    telefono = COALESCE(%s, telefono),
                    codigo_elisa = COALESCE(%s, codigo_elisa),
                    dirty = true
                WHERE id = %s
                RETURNING *
                """,
                (nombre, telefono, partes.get("codigo_elisa"), sugerido),
                fetch_one=True,
            )
            actualizado = run_query(
                """
                UPDATE ventas_import_raw
                SET cliente_id = %s,
                    estado_cliente = 'vinculado',
                    nombre_cliente_limpio = %s,
                    codigo_elisa = COALESCE(codigo_elisa, %s),
                    conflicto_cliente = NULL
                WHERE id = %s
                RETURNING *
                """,
                (sugerido, nombre, partes.get("codigo_elisa"), fila_id),
                fetch_one=True,
            )
            return {
                "success": True,
                "message": f"Nombre actualizado a '{nombre}' y fila vinculada",
                "data": {"cliente": cli, "fila": actualizado},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al actualizar nombre: {e}",
            }

    @staticmethod
    def vincular_manual(fila_id: str, cliente_id: str) -> dict:
        """Vincula manualmente una fila a un cliente existente."""
        try:
            cli = run_query(
                "SELECT id, nombre FROM clientes WHERE id = %s",
                (cliente_id,),
                fetch_one=True,
            )
            if not cli:
                return {"success": False, "message": "Cliente no encontrado"}
            fila = run_query(
                """
                UPDATE ventas_import_raw
                SET cliente_id = %s,
                    estado_cliente = 'vinculado',
                    conflicto_cliente = NULL
                WHERE id = %s
                RETURNING *
                """,
                (cliente_id, fila_id),
                fetch_one=True,
            )
            if not fila:
                return {"success": False, "message": "Fila no encontrada"}
            return {
                "success": True,
                "message": f"Vinculado a '{cli['nombre']}'",
                "data": fila,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al vincular cliente: {e}",
            }
