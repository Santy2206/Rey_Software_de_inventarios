"""
Procesamiento de ventas Elisa (Fase 4).

Toma filas de ventas_import_raw ya resueltas (producto + cliente) y crea
ventas reales reutilizando VentasService.registrar (descuento de stock +
movimientos egreso en la bodega del producto).

Documentación previa (obligatoria):
  - En el catálogo actual, producto_id de fragancias apunta al SKU por
    código (ej. 100M SAUVAGE) en bodegas 'Fragancias Bodega' / 'Venta
    Fragancias'. NO hay filas separadas de "esencia en gramos" vs
    "terminado en unidades": el mismo producto es la referencia de stock.
  - stock_actual / movimientos.cantidad / venta_detalle.cantidad se
    ampliaron a numeric(14,4) para poder descontar gramos decimales de
    combos sin redondeo agresivo.
  - Bodega 'Envases' existe pero hoy no tiene productos cargados: si no
    se resuelve un envase, la fila se marca con error y el lote continúa.

Reglas:
  - Solo filas: estado_resolucion in (vinculado, creado_nuevo),
    estado_cliente=vinculado, es_cuadre_caja=false, procesado=false.
  - Combos: gramos_totales / N códigos con Decimal (4+ decimales) + 1 envase.
  - 41353801 esencia pura: cantidad ya normalizada (g/oz), sin mezcla.
  - OBSEQUIO: descuenta stock igual (total puede ser 0).
  - procesado=true solo tras éxito; error de una fila no detiene el lote.

SIN imports de Flet.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from src.core.local_db import run_query
from src.services.auth_service import AuthService
from src.services.elisa_concepto_parser import (
    gramos_esencia_crema,
    gramos_esencia_por_ml,
)
from src.services.ventas_service import VentasService


# Precisión de descuento de esencia (nunca redondear antes a 1-2 decimales).
_Q4 = Decimal("0.0001")

# Cuentas
_CTA_ALCOHOL = "41353800"
_CTA_ESENCIA = "41353801"
_CTA_PERFUME = "41353802"
_CTA_SPLASH = "41353803"
_CTA_ENVASES = "41353804"
_CTA_CREMAS_EXT = "41353805"
_CTA_AROMA = "41353806"
_CTA_BISUTERIA = "41353807"
_CTA_CREMAS_ELAB = "41353808"
_CTA_ACCESORIOS = "41353809"
_CTA_EMPAQUES = "41353810"
_CTA_ADITIVOS = "41353811"
_CTA_OTROS = "41353814"

_CTAS_PERFUME_MEZCLA = {_CTA_PERFUME, _CTA_CREMAS_ELAB}
_CTAS_SIMPLE_UNIDAD = {
    _CTA_ALCOHOL,
    _CTA_SPLASH,
    _CTA_ENVASES,
    _CTA_CREMAS_EXT,
    _CTA_AROMA,
    _CTA_BISUTERIA,
    _CTA_ACCESORIOS,
    _CTA_EMPAQUES,
    _CTA_ADITIVOS,
    _CTA_OTROS,
}

_RE_OBSEQUIO = re.compile(r"\bOBSEQUIO\b", re.IGNORECASE)


def _d(value, default="0") -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _q4(value) -> Decimal:
    return _d(value).quantize(_Q4, rounding=ROUND_HALF_UP)


def _as_dict(v) -> dict:
    return v if isinstance(v, dict) else {}


def _as_list(v) -> list:
    return v if isinstance(v, list) else []


def _parse_fecha(valor) -> datetime | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    s = str(valor).strip()
    if not s:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _parse_credito(valor) -> Decimal:
    if valor is None:
        return Decimal("0.00")
    s = str(valor).strip().replace("$", "").replace(" ", "")
    # 1.234,56 o 1234.56
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return Decimal(s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _es_obsequio(fila: dict) -> bool:
    attrs = fila.get("atributos")
    if isinstance(attrs, dict) and attrs.get("es_obsequio"):
        return True
    for campo in ("concepto", "concepto_limpio"):
        if _RE_OBSEQUIO.search(str(fila.get(campo) or "")):
            return True
    return False


def _cuenta(fila: dict) -> str:
    # Si el parser reclasificó la fila, la cuenta efectiva manda.
    attrs = fila.get("atributos")
    if isinstance(attrs, dict) and attrs.get("cuenta"):
        return re.sub(r"\D", "", str(attrs["cuenta"]))
    return re.sub(r"\D", "", str(fila.get("cuenta") or ""))


def _buscar_envase(envase: str | None, tamano_ml) -> dict | None:
    """
    Busca un producto de envase en catálogo por familia + tamaño.

    El catálogo usa nombres largos ("CILINDRICO ROSCA LUJO 30 ML") y Elisa
    usa nombres cortos ("CILINDRICO 30ML"). Se normaliza comparando la
    palabra-familia del envase y el tamaño en ml, tolerando palabras
    intermedias (ROSCA, AGRAFE, LUJO, REPLICA...).

    Si no hay match, retorna None (la fila fallará con error específico).
    """
    if not envase or str(envase).upper() == "RECARGA":
        return None
    envase_u = str(envase).upper().strip()
    tam = None
    try:
        if tamano_ml is not None:
            tam = int(round(float(tamano_ml)))
    except Exception:
        tam = None

    # 1) Familia + tamaño exacto (palabra independiente): "CILINDRICO" + 30
    if tam is not None:
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
            LIMIT 20
            """,
            (f"%{envase_u}%", rf"\m{tam}\s*ML"),
        )
        if rows:
            return dict(rows[0])

    # 2) Solo familia en bodega Envases (o nombre que la contenga)
    rows = run_query(
        """
        SELECT p.id, p.nombre, p.codigo, p.bodega_id, b.nombre AS bodega_nombre
        FROM productos p
        JOIN bodegas b ON b.id = p.bodega_id
        WHERE (
            b.nombre ILIKE %s
            OR UPPER(p.nombre) LIKE %s
        )
        ORDER BY
          CASE WHEN b.nombre ILIKE %s THEN 0 ELSE 1 END,
          LENGTH(p.nombre), p.nombre
        LIMIT 20
        """,
        ("%envase%", f"%{envase_u}%", "%envase%"),
    )
    if not rows:
        return None
    if tam is None:
        return dict(rows[0])

    for r in rows:
        nom = (r.get("nombre") or "").upper()
        if str(tam) in re.sub(r"\s+", "", nom):
            return dict(r)
    return dict(rows[0])


def _producto_ids_de_fila(fila: dict) -> list[str]:
    """Lista de producto_id a descontar (simple o combo)."""
    ids: list[str] = []
    vinculados = _as_list(fila.get("productos_vinculados"))
    if vinculados:
        for v in vinculados:
            if isinstance(v, dict) and v.get("producto_id"):
                ids.append(str(v["producto_id"]))
            elif isinstance(v, str):
                ids.append(v)
    if not ids and fila.get("producto_id"):
        ids.append(str(fila["producto_id"]))
    # dedupe preservando orden
    out = []
    seen = set()
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _repartir_gramos(total: Decimal, n: int) -> list[Decimal]:
    """
    Partes iguales con precisión decimal.
    La última parte absorbe el residuo para que sumen exacto el total.
    """
    if n <= 0:
        return []
    if n == 1:
        return [_q4(total)]
    base = (total / Decimal(n)).quantize(_Q4, rounding=ROUND_HALF_UP)
    partes = [base] * (n - 1)
    resto = _q4(total - sum(partes))
    partes.append(resto)
    return partes


def _repartir_total_credito(total: Decimal, pesos: list[Decimal]) -> list[Decimal]:
    """Reparte el CREDITO entre líneas proporcional a cantidad/peso."""
    if not pesos:
        return []
    s = sum(pesos)
    if s <= 0 or total == 0:
        return [Decimal("0.00")] * len(pesos)
    monedas = []
    acum = Decimal("0.00")
    for i, w in enumerate(pesos):
        if i == len(pesos) - 1:
            monedas.append(_d(total) - acum)
        else:
            parte = (total * w / s).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            monedas.append(parte)
            acum += parte
    return monedas


class VentasProcesoService:
    """Convierte filas import_raw resueltas en ventas + movimientos reales."""

    @staticmethod
    def _marcar_error(fila_id: str, mensaje: str):
        run_query(
            """
            UPDATE ventas_import_raw
            SET estado_proceso = 'error',
                error_proceso = %s,
                procesado = false
            WHERE id = %s
            """,
            ((mensaje or "")[:1000], fila_id),
        )

    @staticmethod
    def _marcar_ok(fila_id: str, venta_id: str):
        run_query(
            """
            UPDATE ventas_import_raw
            SET procesado = true,
                estado_proceso = 'procesado',
                venta_id = %s,
                error_proceso = NULL
            WHERE id = %s
            """,
            (venta_id, fila_id),
        )

    @staticmethod
    def construir_items(fila: dict) -> dict:
        """
        Construye las líneas de venta a partir de una fila import_raw.

        Retorna {"success", "message", "data": {"items": [...], "meta": {...}}}
        """
        try:
            attrs = _as_dict(fila.get("atributos"))
            cuenta = _cuenta(fila)
            cantidad_fila = int(fila.get("cantidad") or attrs.get("cantidad") or 1)
            if cantidad_fila <= 0:
                cantidad_fila = 1

            producto_ids = _producto_ids_de_fila(fila)
            if not producto_ids:
                return {
                    "success": False,
                    "message": "Fila sin producto_id / productos_vinculados",
                    "data": None,
                }

            items: list[dict] = []
            meta: dict[str, Any] = {
                "cuenta": cuenta,
                "es_combo": bool(attrs.get("es_combo")) or len(producto_ids) > 1,
                "envase": attrs.get("envase"),
                "tamano_ml": attrs.get("tamano_ml"),
            }

            # ---- 802 / 808 perfume o crema elaborada ----
            if cuenta in _CTAS_PERFUME_MEZCLA or meta["es_combo"]:
                tamano = attrs.get("tamano_ml")
                gramos = attrs.get("gramos_esencia_total")
                if gramos is None:
                    if cuenta == _CTA_CREMAS_ELAB:
                        gramos = gramos_esencia_crema(tamano)
                    else:
                        gramos = gramos_esencia_por_ml(tamano)
                if gramos is None:
                    return {
                        "success": False,
                        "message": (
                            f"Sin regla de esencia para {tamano} ml "
                            "(cuenta perfume/crema)"
                        ),
                        "data": None,
                    }
                gramos_total = _q4(Decimal(str(gramos)) * cantidad_fila)
                n = len(producto_ids)
                partes = _repartir_gramos(gramos_total, n)
                meta["gramos_total"] = float(gramos_total)
                meta["gramos_por_codigo"] = [float(p) for p in partes]
                for pid, g in zip(producto_ids, partes):
                    items.append({"producto_id": pid, "cantidad": g})

                envase = attrs.get("envase")
                if envase and str(envase).upper() != "RECARGA":
                    env = _buscar_envase(envase, tamano)
                    if not env:
                        return {
                            "success": False,
                            "message": (
                                f"Envase no encontrado en catálogo: "
                                f"{envase} {tamano}ml"
                            ),
                            "data": None,
                        }
                    items.append(
                        {
                            "producto_id": str(env["id"]),
                            "cantidad": Decimal(cantidad_fila),
                        }
                    )
                    meta["envase_id"] = str(env["id"])
                    meta["envase_nombre"] = env.get("nombre")
                return {"success": True, "message": "OK", "data": {"items": items, "meta": meta}}

            # ---- 801 esencia pura ----
            if cuenta == _CTA_ESENCIA:
                # cantidad_base_g si existe; si no, cantidad de la fila
                base_g = attrs.get("cantidad_base_g")
                if base_g is not None:
                    cant = _q4(Decimal(str(base_g)) * cantidad_fila)
                else:
                    origen = attrs.get("cantidad_origen")
                    unidad = (attrs.get("unidad_origen") or "").lower()
                    if origen is not None and unidad == "oz":
                        cant = _q4(Decimal(str(origen)) * Decimal("28.35") * cantidad_fila)
                    elif origen is not None and unidad in ("g", "gr"):
                        cant = _q4(Decimal(str(origen)) * cantidad_fila)
                    else:
                        cant = _q4(Decimal(cantidad_fila))
                for pid in producto_ids:
                    items.append({"producto_id": pid, "cantidad": cant})
                return {"success": True, "message": "OK", "data": {"items": items, "meta": meta}}

            # ---- resto: 1 unidad (o N UND) por producto ----
            cant = Decimal(cantidad_fila)
            for pid in producto_ids:
                items.append({"producto_id": pid, "cantidad": cant})

            # 804 envases: ya es el envase en sí, no agregar otro
            return {"success": True, "message": "OK", "data": {"items": items, "meta": meta}}

        except Exception as e:
            return {
                "success": False,
                "message": f"Error al construir items: {e}",
                "data": None,
            }

    @staticmethod
    def procesar_fila(fila: dict, usuario_id: str | None = None) -> dict:
        """
        Procesa una sola fila import_raw → venta real.
        Marca procesado/error en la propia fila.
        """
        fila_id = str(fila["id"])
        try:
            if fila.get("procesado"):
                return {
                    "success": True,
                    "message": "Fila ya procesada",
                    "data": {"ya_procesada": True},
                }
            if fila.get("es_cuadre_caja"):
                VentasProcesoService._marcar_error(
                    fila_id, "Cuadre de caja: no genera venta automática"
                )
                return {
                    "success": False,
                    "message": "Cuadre de caja",
                    "data": None,
                }
            if fila.get("estado_resolucion") not in ("vinculado", "creado_nuevo"):
                VentasProcesoService._marcar_error(
                    fila_id, "Producto no resuelto"
                )
                return {"success": False, "message": "Producto no resuelto", "data": None}
            if fila.get("estado_cliente") != "vinculado" or not fila.get("cliente_id"):
                VentasProcesoService._marcar_error(
                    fila_id, "Cliente no resuelto"
                )
                return {"success": False, "message": "Cliente no resuelto", "data": None}

            built = VentasProcesoService.construir_items(fila)
            if not built.get("success"):
                VentasProcesoService._marcar_error(fila_id, built.get("message") or "Error items")
                return built

            items = built["data"]["items"]
            meta = built["data"]["meta"]
            credito = _parse_credito(fila.get("credito"))
            if _es_obsequio(fila):
                # stock se descuenta; total puede quedar 0
                credito = Decimal("0.00")
                meta["obsequio"] = True

            # Repartir total del archivo entre líneas (para el total de venta).
            # Los precios unitarios internos se derivan; el total forzado es el CREDITO.
            pesos = [_q4(i["cantidad"]) for i in items]
            subtotales = _repartir_total_credito(credito, pesos)
            lineas = []
            for item, sub in zip(items, subtotales):
                cant = _q4(item["cantidad"])
                if cant > 0 and sub is not None:
                    punit = (sub / cant).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                else:
                    punit = Decimal("0.00")
                lineas.append(
                    {
                        "producto_id": item["producto_id"],
                        "cantidad": cant,
                        "precio_unitario": punit,
                        "subtotal": sub,
                    }
                )

            fecha = _parse_fecha(fila.get("fecha"))
            uid = usuario_id or AuthService.get_usuario_id()

            result = VentasService.registrar(
                cliente_id=str(fila["cliente_id"]),
                items=lineas,
                usuario_id=uid,
                fecha=fecha,
                total_forzado=credito,
                # Import histórico: el catálogo puede tener stock 0 aún no
                # cargado; se permite negativo para no bloquear el descuento
                # real de la venta Elisa. La UI manual sigue con default False.
                permitir_stock_negativo=True,
                motivo_movimiento=f"ELISA {fila.get('fila_origen')}",
            )
            if not result.get("success"):
                VentasProcesoService._marcar_error(
                    fila_id, result.get("message") or "Error al registrar venta"
                )
                return result

            venta = result["data"]
            venta_id = str(venta["id"])
            VentasProcesoService._marcar_ok(fila_id, venta_id)
            return {
                "success": True,
                "message": f"Venta {venta_id} creada",
                "data": {"venta": venta, "meta": meta, "items": lineas},
            }
        except Exception as e:
            VentasProcesoService._marcar_error(fila_id, str(e))
            return {
                "success": False,
                "message": f"Error al procesar fila: {e}",
                "data": None,
            }

    @staticmethod
    def get_filas_listas(lote_id: str | None = None, limite: int = 500) -> dict:
        try:
            params: list = []
            where = """
                WHERE procesado = false
                  AND es_cuadre_caja = false
                  AND COALESCE(es_duplicado_omitido, false) = false
                  AND estado_resolucion IN ('vinculado', 'creado_nuevo')
                  AND estado_cliente = 'vinculado'
                  AND COALESCE(estado_proceso, 'pendiente') IN ('pendiente', 'error')
            """
            if lote_id:
                where += " AND lote_id = %s"
                params.append(lote_id)
            params.append(limite)
            data = run_query(
                f"""
                SELECT *
                FROM ventas_import_raw
                {where}
                ORDER BY fila_origen
                LIMIT %s
                """,
                tuple(params),
            )
            return {
                "success": True,
                "message": f"{len(data or [])} fila(s) listas",
                "data": data or [],
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al listar filas listas: {e}",
                "data": [],
            }

    @staticmethod
    def procesar_lote(lote_id: str, usuario_id: str | None = None) -> dict:
        """
        Procesa todas las filas listas de un lote.
        Un error en una fila no detiene las demás.
        """
        print(f"--- Procesando ventas Elisa lote {lote_id} ---")
        try:
            res = VentasProcesoService.get_filas_listas(lote_id=lote_id, limite=5000)
            if not res.get("success"):
                return res
            filas = res["data"]
            if not filas:
                return {
                    "success": True,
                    "message": "No hay filas listas para procesar en el lote",
                    "data": {
                        "lote_id": lote_id,
                        "ok": 0,
                        "error": 0,
                        "total": 0,
                    },
                }

            ok = err = 0
            errores = []
            for fila in filas:
                r = VentasProcesoService.procesar_fila(fila, usuario_id=usuario_id)
                if r.get("success") and not (r.get("data") or {}).get("ya_procesada"):
                    ok += 1
                elif r.get("success"):
                    ok += 1
                else:
                    err += 1
                    errores.append(
                        {
                            "fila_id": str(fila["id"]),
                            "fila_origen": fila.get("fila_origen"),
                            "message": r.get("message"),
                        }
                    )

            resumen = {
                "lote_id": lote_id,
                "ok": ok,
                "error": err,
                "total": len(filas),
                "errores": errores[:50],
            }
            print(f" Proceso lote: {resumen}")
            return {
                "success": err == 0,
                "message": f"Procesadas {ok} ok, {err} con error (de {len(filas)})",
                "data": resumen,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al procesar lote: {e}",
                "data": None,
            }

    @staticmethod
    def procesar_pendientes(usuario_id: str | None = None) -> dict:
        try:
            lotes = run_query(
                """
                SELECT DISTINCT lote_id
                FROM ventas_import_raw
                WHERE procesado = false
                  AND es_cuadre_caja = false
                  AND COALESCE(es_duplicado_omitido, false) = false
                  AND estado_resolucion IN ('vinculado', 'creado_nuevo')
                  AND estado_cliente = 'vinculado'
                """
            )
            if not lotes:
                return {
                    "success": True,
                    "message": "No hay filas listas para procesar",
                    "data": {"lotes": 0},
                }
            detalle = []
            for row in lotes:
                r = VentasProcesoService.procesar_lote(
                    str(row["lote_id"]), usuario_id=usuario_id
                )
                detalle.append(r.get("data"))
            return {
                "success": True,
                "message": f"Procesados {len(lotes)} lote(s)",
                "data": {"lotes": len(lotes), "detalle": detalle},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error al procesar pendientes: {e}",
                "data": None,
            }
