"""
Resolución de filas Elisa contra el catálogo de productos (Fase 2).

Para cada fila de ventas_import_raw (procesado=false, es_cuadre_caja=false):
  1. Construye clave(s) de búsqueda a partir de atributos.
  2. Busca coincidencia exacta por codigo / nombre.
  3. Si no hay exacta, sugiere hasta 5 candidatos por similitud pg_trgm.
  4. NUNCA crea productos automáticamente.

Acciones manuales sobre filas pendientes:
  - vincular(producto_id)
  - crear_producto_nuevo(...)  — el usuario elige crear; no es automático
  - descartar(motivo)

Estados de resolución:
  pendiente | vinculado | creado_nuevo | descartado | no_aplica

SIN imports de Flet. Contrato estándar {"success","message","data"}.
"""

from __future__ import annotations

from psycopg2.extras import Json

from src.core.local_db import get_cursor, run_query
from src.services.auth_service import AuthService
from src.services.productos_service import ProductosService


# Umbral mínimo de similitud pg_trgm (0..1) para sugerir candidatos.
UMBRAL_SIMILITUD_DEFAULT = 0.25
MAX_CANDIDATOS = 5

ESTADOS = (
    "pendiente",
    "vinculado",
    "creado_nuevo",
    "descartado",
    "no_aplica",
)


def _as_dict(attrs) -> dict:
    if attrs is None:
        return {}
    if isinstance(attrs, dict):
        return attrs
    return {}


def _build_claves(atributos: dict) -> dict:
    """
    Claves de búsqueda a partir de atributos de Fase 1.

    Retorna:
      {
        "codigos": [str],
        "nombre": str|None,
        "clave_busqueda": str,   # texto representativo
        "es_combo": bool,
      }
    """
    attrs = _as_dict(atributos)
    codigos = attrs.get("codigos") or []
    if not codigos and attrs.get("codigo"):
        codigos = [attrs["codigo"]]
    codigos = [str(c).upper().strip() for c in codigos if c]

    nombre = (attrs.get("nombre") or "").strip() or None
    envase = attrs.get("envase")
    tamano = attrs.get("tamano_ml")
    partes = []
    if codigos:
        partes.append("+".join(codigos))
    if nombre:
        partes.append(nombre)
    # evitar duplicar el envase si ya viene en el nombre
    if envase and str(envase).upper() not in (nombre or "").upper():
        partes.append(str(envase))
    if tamano:
        # 30.0 -> "30ML", no "30.0ML"
        try:
            t = float(tamano)
            partes.append(f"{int(t) if t == int(t) else t}ML")
        except (TypeError, ValueError):
            partes.append(f"{tamano}ML")
    clave = " ".join(partes).strip() or (attrs.get("concepto_limpio") or "")

    return {
        "codigos": codigos,
        "nombre": nombre,
        "clave_busqueda": clave.upper() if clave else None,
        "es_combo": bool(attrs.get("es_combo")) or len(codigos) > 1,
        "categoria": attrs.get("categoria"),
    }


class VentasResolucionService:
    """Matching y cola de revisión de importación Elisa."""

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    @staticmethod
    def buscar_candidatos(
        clave: str | None = None,
        codigo: str | None = None,
        umbral: float = UMBRAL_SIMILITUD_DEFAULT,
        limite: int = MAX_CANDIDATOS,
        bodega_id: str | None = None,
    ) -> dict:
        """
        Busca productos candidatos.

        Orden:
          1) match exacto por codigo
          2) match exacto por nombre (case-insensitive)
          3) similitud pg_trgm sobre nombre y codigo
        """
        try:
            resultados: list[dict] = []
            vistos: set[str] = set()

            def _add(rows, motivo: str):
                for r in rows or []:
                    pid = str(r["id"])
                    if pid in vistos:
                        continue
                    vistos.add(pid)
                    resultados.append(
                        {
                            "id": pid,
                            "nombre": r.get("nombre"),
                            "codigo": r.get("codigo"),
                            "bodega_id": str(r["bodega_id"]) if r.get("bodega_id") else None,
                            "bodega_nombre": r.get("bodega_nombre"),
                            "score": float(r.get("score") or 1.0),
                            "motivo": motivo,
                        }
                    )

            codigo_norm = (codigo or "").strip().upper() or None
            clave_norm = (clave or "").strip() or None
            filtro_bodega = " AND p.bodega_id = %s::uuid" if bodega_id else ""
            extra = (bodega_id,) if bodega_id else ()

            if codigo_norm:
                exactos = run_query(
                    f"""
                    SELECT p.id, p.nombre, p.codigo, p.bodega_id,
                           b.nombre AS bodega_nombre,
                           1.0::float AS score
                    FROM productos p
                    LEFT JOIN bodegas b ON b.id = p.bodega_id
                    WHERE UPPER(TRIM(p.codigo)) = %s{filtro_bodega}
                    ORDER BY p.nombre
                    LIMIT %s
                    """,
                    (codigo_norm, *extra, limite),
                )
                _add(exactos, "codigo_exacto")

            if clave_norm and len(resultados) < limite:
                exactos_nom = run_query(
                    f"""
                    SELECT p.id, p.nombre, p.codigo, p.bodega_id,
                           b.nombre AS bodega_nombre,
                           1.0::float AS score
                    FROM productos p
                    LEFT JOIN bodegas b ON b.id = p.bodega_id
                    WHERE UPPER(TRIM(p.nombre)) = UPPER(TRIM(%s)){filtro_bodega}
                    ORDER BY p.nombre
                    LIMIT %s
                    """,
                    (clave_norm, *extra, limite),
                )
                _add(exactos_nom, "nombre_exacto")

            if clave_norm and len(resultados) < limite:
                faltan = limite - len(resultados)
                fuzzy = run_query(
                    f"""
                    SELECT p.id, p.nombre, p.codigo, p.bodega_id,
                           b.nombre AS bodega_nombre,
                           GREATEST(
                               similarity(COALESCE(p.nombre, ''), %s),
                               similarity(COALESCE(p.codigo, ''), %s)
                           ) AS score
                    FROM productos p
                    LEFT JOIN bodegas b ON b.id = p.bodega_id
                    WHERE GREATEST(
                              similarity(COALESCE(p.nombre, ''), %s),
                              similarity(COALESCE(p.codigo, ''), %s)
                          ) >= %s{filtro_bodega}
                    ORDER BY score DESC, p.nombre
                    LIMIT %s
                    """,
                    (
                        clave_norm,
                        clave_norm,
                        clave_norm,
                        clave_norm,
                        umbral,
                        *extra,
                        faltan + 10,  # margen por filtrar duplicados
                    ),
                )
                _add(fuzzy, "similitud")

            return {
                "success": True,
                "message": f"{len(resultados[:limite])} candidato(s)",
                "data": resultados[:limite],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al buscar candidatos: {e}",
                "data": [],
            }

    @staticmethod
    def _buscar_envase_exacto(envase: str, tamano_ml) -> dict | None:
        """
        Match único de envase por familia + tamaño (palabra independiente).
        Retorna el producto si hay exactamente un candidato; si hay varios
        o ninguno, None (queda pendiente con sus candidatos fuzzy).
        """
        envase_u = str(envase).upper().strip()
        try:
            tam = int(round(float(tamano_ml))) if tamano_ml is not None else None
        except (TypeError, ValueError):
            tam = None
        if tam is None:
            return None
        rows = run_query(
            """
            SELECT p.id, p.nombre, p.codigo, p.bodega_id,
                   b.nombre AS bodega_nombre
            FROM productos p
            JOIN bodegas b ON b.id = p.bodega_id
            WHERE UPPER(p.nombre) LIKE %s
              AND p.nombre ~* %s
            ORDER BY
              CASE WHEN b.nombre ILIKE '%%envase%%' THEN 0 ELSE 1 END,
              LENGTH(p.nombre), p.nombre
            LIMIT 5
            """,
            (f"%{envase_u}%", rf"\m{tam}\s*ML"),
        )
        if rows and len(rows) == 1:
            return {
                "id": str(rows[0]["id"]),
                "nombre": rows[0]["nombre"],
            }
        return None

    @staticmethod
    def _resolver_fila(fila: dict, umbral: float) -> dict:
        """
        Calcula estado/candidatos para una sola fila import_raw.
        No escribe en BD (solo prepara el payload de UPDATE).
        """
        if fila.get("es_cuadre_caja"):
            return {
                "estado_resolucion": "no_aplica",
                "producto_id": None,
                "productos_vinculados": None,
                "candidatos": None,
                "clave_busqueda": None,
            }

        attrs = _as_dict(fila.get("atributos"))
        claves = _build_claves(attrs)
        clave = claves["clave_busqueda"]
        codigos = claves["codigos"]

        # Reuso automático: si otra fila con el mismo concepto/clave ya fue
        # vinculada o creada, copiar su producto sin volver a preguntar.
        previa = run_query(
            """
            SELECT r.producto_id, r.productos_vinculados
            FROM ventas_import_raw r
            WHERE r.id <> %s
              AND r.estado_resolucion IN ('vinculado', 'creado_nuevo')
              AND (
                  (r.clave_busqueda IS NOT NULL
                       AND %s IS NOT NULL
                       AND UPPER(r.clave_busqueda) = UPPER(%s))
                  OR UPPER(r.concepto_limpio) = UPPER(%s)
              )
            ORDER BY r.creado_en DESC
            LIMIT 1
            """,
            (
                str(fila.get("id")),
                clave,
                clave,
                fila.get("concepto_limpio") or "",
            ),
            fetch_one=True,
        )
        if previa and (previa.get("producto_id") or previa.get("productos_vinculados")):
            return {
                "estado_resolucion": "vinculado",
                "producto_id": str(previa["producto_id"]) if previa.get("producto_id") else None,
                "productos_vinculados": previa.get("productos_vinculados"),
                "candidatos": None,
                "clave_busqueda": clave,
            }

        def _preferir_venta(exactos: list) -> list:
            """
            Si el mismo código existe en varias bodegas, preferir la bodega
            de venta (nombre contiene 'VENTA'). Retorna lista reducida.
            """
            if len(exactos) <= 1:
                return exactos
            venta = [
                c for c in exactos
                if "VENTA" in (c.get("bodega_nombre") or "").upper()
            ]
            return venta if venta else exactos


        # Combos: intentar match exacto por cada código
        if claves["es_combo"] and codigos:
            vinculados = []
            candidatos_combo = []
            todos_exactos = True
            for cod in codigos:
                res = VentasResolucionService.buscar_candidatos(
                    codigo=cod, umbral=umbral
                )
                cands = res.get("data") or []
                exactos = [c for c in cands if c.get("motivo") == "codigo_exacto"]
                exactos = _preferir_venta(exactos)
                if exactos:
                    # Si hay varios (mismo código en bodegas distintas) se toma el primero
                    # y se dejan todos en candidatos para revisión si hay ambigüedad.
                    vinculados.append(
                        {
                            "codigo": cod,
                            "producto_id": exactos[0]["id"],
                            "nombre": exactos[0]["nombre"],
                            "ambiguo": len(exactos) > 1,
                        }
                    )
                    if len(exactos) > 1:
                        todos_exactos = False
                        candidatos_combo.extend(exactos)
                else:
                    todos_exactos = False
                    if cands:
                        candidatos_combo.extend(cands)
                    else:
                        # fuzzy con el código solo
                        fuzzy = VentasResolucionService.buscar_candidatos(
                            clave=cod, codigo=None, umbral=umbral
                        )
                        candidatos_combo.extend(fuzzy.get("data") or [])

            if todos_exactos and vinculados and not any(v.get("ambiguo") for v in vinculados):
                return {
                    "estado_resolucion": "vinculado",
                    "producto_id": None,
                    "productos_vinculados": vinculados,
                    "candidatos": None,
                    "clave_busqueda": clave,
                }

            # dedupe candidatos
            vistos = set()
            cands_final = []
            for c in candidatos_combo:
                if c["id"] in vistos:
                    continue
                vistos.add(c["id"])
                cands_final.append(c)
            return {
                "estado_resolucion": "pendiente",
                "producto_id": None,
                "productos_vinculados": vinculados or None,
                "candidatos": cands_final[:MAX_CANDIDATOS] or None,
                "clave_busqueda": clave,
            }

        # Envase sin código de fragancia: match por familia + tamaño.
        # "CILINDRICO 30ML" → "CILINDRICO ROSCA LUJO 30 ML"
        envase = attrs.get("envase")
        tamano = attrs.get("tamano_ml")
        if not codigos and envase and str(envase).upper() != "RECARGA":
            env_res = VentasResolucionService._buscar_envase_exacto(
                envase, tamano
            )
            if env_res is not None:
                return {
                    "estado_resolucion": "vinculado",
                    "producto_id": env_res["id"],
                    "productos_vinculados": None,
                    "candidatos": None,
                    "clave_busqueda": clave,
                }

        # Producto simple
        codigo = codigos[0] if len(codigos) == 1 else None
        res = VentasResolucionService.buscar_candidatos(
            clave=clave or claves["nombre"],
            codigo=codigo,
            umbral=umbral,
        )
        cands = res.get("data") or []
        exactos = [
            c for c in cands if c.get("motivo") in ("codigo_exacto", "nombre_exacto")
        ]

        exactos = _preferir_venta(exactos)

        if len(exactos) == 1:
            return {
                "estado_resolucion": "vinculado",
                "producto_id": exactos[0]["id"],
                "productos_vinculados": None,
                "candidatos": None,
                "clave_busqueda": clave,
            }

        # 0 o varios exactos / solo fuzzy → pendiente con sugerencias
        return {
            "estado_resolucion": "pendiente",
            "producto_id": None,
            "productos_vinculados": None,
            "candidatos": cands or None,
            "clave_busqueda": clave,
        }

    @staticmethod
    def resolver_lote(lote_id: str, umbral: float = UMBRAL_SIMILITUD_DEFAULT) -> dict:
        """
        Recorre un lote y aplica matching. Actualiza estado_resolucion /
        producto_id / candidatos. No marca procesado=true (eso es fases 3–5).
        """
        print(f"--- Resolviendo lote Elisa {lote_id} ---")
        try:
            filas = run_query(
                """
                SELECT *
                FROM ventas_import_raw
                WHERE lote_id = %s
                  AND COALESCE(es_duplicado_omitido, false) = false
                  AND estado_resolucion IN ('pendiente', 'no_aplica')
                ORDER BY fila_origen
                """,
                (lote_id,),
            )
            if not filas:
                return {
                    "success": True,
                    "message": "No hay filas pendientes en el lote",
                    "data": {"lote_id": lote_id, "vinculados": 0, "pendientes": 0},
                }

            vinculados = 0
            pendientes = 0
            no_aplica = 0

            with get_cursor() as cur:
                for fila in filas:
                    payload = VentasResolucionService._resolver_fila(fila, umbral)
                    estado = payload["estado_resolucion"]
                    if estado == "vinculado":
                        vinculados += 1
                    elif estado == "no_aplica":
                        no_aplica += 1
                    else:
                        pendientes += 1

                    cur.execute(
                        """
                        UPDATE ventas_import_raw
                        SET estado_resolucion = %s,
                            producto_id = %s,
                            productos_vinculados = %s,
                            candidatos = %s,
                            clave_busqueda = %s,
                            motivo_descarte = CASE
                                WHEN %s = 'descartado' THEN motivo_descarte
                                ELSE NULL
                            END
                        WHERE id = %s
                        """,
                        (
                            estado,
                            payload["producto_id"],
                            Json(payload["productos_vinculados"])
                            if payload["productos_vinculados"] is not None
                            else None,
                            Json(payload["candidatos"])
                            if payload["candidatos"] is not None
                            else None,
                            payload["clave_busqueda"],
                            estado,
                            fila["id"],
                        ),
                    )

            resumen = {
                "lote_id": lote_id,
                "total": len(filas),
                "vinculados": vinculados,
                "pendientes": pendientes,
                "no_aplica": no_aplica,
            }
            print(f" Resolución lote: {resumen}")
            return {
                "success": True,
                "message": (
                    f"Resolución: {vinculados} vinculados, "
                    f"{pendientes} pendientes, {no_aplica} no aplican"
                ),
                "data": resumen,
            }
        except Exception as e:
            error_msg = str(e)
            print(f" Error en resolver_lote: {error_msg}")
            return {
                "success": False,
                "message": f"Error al resolver lote: {error_msg}",
                "data": None,
            }

    @staticmethod
    def resolver_pendientes(umbral: float = UMBRAL_SIMILITUD_DEFAULT) -> dict:
        """Resuelve todas las filas pendientes de todos los lotes."""
        try:
            lotes = run_query(
                """
                SELECT DISTINCT lote_id
                FROM ventas_import_raw
                WHERE estado_resolucion = 'pendiente'
                  AND es_cuadre_caja = false
                  AND COALESCE(es_duplicado_omitido, false) = false
                """
            )
            if not lotes:
                return {
                    "success": True,
                    "message": "No hay filas pendientes",
                    "data": {"lotes": 0},
                }
            resultados = []
            for row in lotes:
                r = VentasResolucionService.resolver_lote(str(row["lote_id"]), umbral)
                resultados.append(r.get("data"))
            return {
                "success": True,
                "message": f"Procesados {len(lotes)} lote(s)",
                "data": {"lotes": len(lotes), "detalle": resultados},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al resolver pendientes: {e}",
                "data": None,
            }

    # ------------------------------------------------------------------
    # Cola de revisión
    # ------------------------------------------------------------------

    @staticmethod
    def get_pendientes(lote_id: str | None = None, limite: int = 200) -> dict:
        """Lista filas en estado pendiente (para la vista de revisión)."""
        try:
            params: list = []
            where = (
                "WHERE r.estado_resolucion = 'pendiente' "
                "AND r.es_cuadre_caja = false "
                "AND COALESCE(r.es_duplicado_omitido, false) = false"
            )
            if lote_id:
                where += " AND r.lote_id = %s"
                params.append(lote_id)
            params.append(limite)
            data = run_query(
                f"""
                SELECT r.*,
                       p.nombre AS producto_nombre,
                       p.codigo AS producto_codigo
                FROM ventas_import_raw r
                LEFT JOIN productos p ON p.id = r.producto_id
                {where}
                ORDER BY r.creado_en DESC, r.fila_origen
                LIMIT %s
                """,
                tuple(params),
            )
            return {
                "success": True,
                "message": f"{len(data or [])} pendiente(s)",
                "data": data or [],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al listar pendientes: {e}",
                "data": [],
            }

    @staticmethod
    def get_resumen_estados(lote_id: str | None = None) -> dict:
        try:
            params: list = []
            where = ""
            if lote_id:
                where = "WHERE lote_id = %s"
                params.append(lote_id)
            data = run_query(
                f"""
                SELECT estado_resolucion, COUNT(*) AS n
                FROM ventas_import_raw
                {where}
                GROUP BY estado_resolucion
                ORDER BY estado_resolucion
                """,
                tuple(params) if params else (),
            )
            return {"success": True, "message": "Resumen", "data": data or []}
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al resumir estados: {e}",
                "data": [],
            }

    @staticmethod
    def vincular(fila_id: str, producto_id: str) -> dict:
        """Vincula manualmente una fila pendiente a un producto existente."""
        print(f"--- Vinculando fila {fila_id} -> producto {producto_id} ---")
        try:
            if not fila_id or not producto_id:
                return {"success": False, "message": "fila_id y producto_id son obligatorios"}

            prod = run_query(
                "SELECT id, nombre, codigo FROM productos WHERE id = %s",
                (producto_id,),
                fetch_one=True,
            )
            if not prod:
                return {"success": False, "message": "Producto no encontrado"}

            fila = run_query(
                """
                UPDATE ventas_import_raw
                SET estado_resolucion = 'vinculado',
                    producto_id = %s,
                    productos_vinculados = NULL,
                    candidatos = NULL,
                    motivo_descarte = NULL
                WHERE id = %s
                  AND es_cuadre_caja = false
                RETURNING *
                """,
                (producto_id, fila_id),
                fetch_one=True,
            )
            if not fila:
                return {
                    "success": False,
                    "message": "Fila no encontrada o es cuadre de caja",
                }
            return {
                "success": True,
                "message": f"Vinculado a '{prod['nombre']}'",
                "data": fila,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al vincular: {e}",
            }

    @staticmethod
    def crear_producto_nuevo(
        fila_id: str,
        bodega_id: str | None = None,
        nombre: str | None = None,
        codigo: str | None = None,
        precio: float = 0.0,
    ) -> dict:
        """
        Crea un producto NUEVO a partir de la fila y lo vincula.
        Acción explícita del usuario — nunca se ejecuta sola.
        Si bodega_id no se pasa, usa la bodega sugerida por el grupo.
        """
        print(f"--- Crear producto desde fila {fila_id} ---")
        try:
            if not fila_id:
                return {"success": False, "message": "fila_id es obligatorio"}

            fila = run_query(
                "SELECT * FROM ventas_import_raw WHERE id = %s",
                (fila_id,),
                fetch_one=True,
            )
            if not fila:
                return {"success": False, "message": "Fila no encontrada"}
            if fila.get("es_cuadre_caja"):
                return {
                    "success": False,
                    "message": "No se puede crear producto desde un cuadre de caja",
                }

            attrs = _as_dict(fila.get("atributos"))

            if not bodega_id:
                sug = attrs.get("bodega_sugerida")
                if sug:
                    b = run_query(
                        "SELECT id FROM bodegas WHERE nombre ILIKE %s LIMIT 1",
                        (sug,), fetch_one=True,
                    )
                    if b:
                        bodega_id = str(b["id"])
            if not bodega_id:
                return {
                    "success": False,
                    "message": "bodega_id es obligatorio (no hay bodega sugerida)",
                }

            nombre_final = (nombre or attrs.get("nombre") or fila.get("concepto_limpio") or "").strip()
            if not nombre_final:
                return {"success": False, "message": "El nombre del producto es obligatorio"}

            codigo_final = codigo
            if codigo_final is None:
                codigo_final = attrs.get("codigo")
                if not codigo_final:
                    codigos = attrs.get("codigos") or []
                    if len(codigos) == 1:
                        codigo_final = codigos[0]

            creado = ProductosService.create(
                nombre=nombre_final,
                bodega_id=bodega_id,
                codigo=codigo_final,
                precio=precio,
                stock_actual=0,
            )
            if not creado.get("success"):
                return creado

            producto = creado["data"]
            actualizado = run_query(
                """
                UPDATE ventas_import_raw
                SET estado_resolucion = 'creado_nuevo',
                    producto_id = %s,
                    productos_vinculados = NULL,
                    candidatos = NULL,
                    motivo_descarte = NULL
                WHERE id = %s
                RETURNING *
                """,
                (producto["id"], fila_id),
                fetch_one=True,
            )
            return {
                "success": True,
                "message": f"Producto '{nombre_final}' creado y vinculado",
                "data": {"producto": producto, "fila": actualizado},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al crear producto: {e}",
            }

    @staticmethod
    def descartar(fila_id: str, motivo: str) -> dict:
        """Descarta una fila pendiente. El motivo es obligatorio."""
        print(f"--- Descartando fila {fila_id} ---")
        try:
            motivo_limpio = (motivo or "").strip()
            if not motivo_limpio:
                return {
                    "success": False,
                    "message": "El motivo de descarte es obligatorio",
                }
            fila = run_query(
                """
                UPDATE ventas_import_raw
                SET estado_resolucion = 'descartado',
                    producto_id = NULL,
                    productos_vinculados = NULL,
                    candidatos = NULL,
                    motivo_descarte = %s
                WHERE id = %s
                  AND es_cuadre_caja = false
                RETURNING *
                """,
                (motivo_limpio[:500], fila_id),
                fetch_one=True,
            )
            if not fila:
                return {
                    "success": False,
                    "message": "Fila no encontrada o es cuadre de caja",
                }
            return {
                "success": True,
                "message": "Fila descartada",
                "data": fila,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al descartar: {e}",
            }

    @staticmethod
    def buscar_productos_manual(
        texto: str, limite: int = 20, bodega_id: str | None = None
    ) -> dict:
        """Búsqueda libre para el diálogo de vinculación manual."""
        q = (texto or "").strip()
        if not q and not bodega_id:
            return {"success": True, "message": "Vacío", "data": []}
        if not q and bodega_id:
            rows = run_query(
                """
                SELECT p.id, p.nombre, p.codigo, p.bodega_id,
                       b.nombre AS bodega_nombre, 1.0::float AS score
                FROM productos p
                LEFT JOIN bodegas b ON b.id = p.bodega_id
                WHERE p.bodega_id = %s::uuid
                ORDER BY p.nombre
                LIMIT %s
                """,
                (bodega_id, limite),
            )
            data = [
                {
                    "id": str(r["id"]),
                    "nombre": r.get("nombre"),
                    "codigo": r.get("codigo"),
                    "bodega_id": str(r["bodega_id"]) if r.get("bodega_id") else None,
                    "bodega_nombre": r.get("bodega_nombre"),
                    "score": 1.0,
                    "motivo": "bodega",
                }
                for r in rows or []
            ]
            return {"success": True, "message": f"{len(data)} en bodega", "data": data}
        return VentasResolucionService.buscar_candidatos(
            clave=q or None,
            codigo=q if q and len(q) <= 10 else None,
            umbral=0.2,
            limite=limite,
            bodega_id=bodega_id,
        )
