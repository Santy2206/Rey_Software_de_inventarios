"""
Parser de CONCEPTO de ventas Elisa (Fase 1).

Responsabilidades de esta fase:
  - Limpiar texto libre digitado a mano (tipeos, espacios, mayúsculas).
  - Extraer cantidad (N UND) y descuento (%DESCUENTO) por separado.
  - Extraer atributos de producto según el código de CUENTA.
  - Dejar combos (códigos unidos por '+') estructurados sin repartir
    aún la esencia (eso es Fase 4).
  - Exponer la tabla de mezcla ml → gramos de esencia (802/808).

NO toca productos, clientes ni movimientos.
SIN imports de Flet.
"""

from __future__ import annotations

import re
from typing import Any


# Tabla de mezcla ml envase → gramos de esencia (perfumería personal).
# Solo aplica a cuentas 41353802 y 41353808. Se reutilizará en Fase 4.
MEZCLA_ML_A_GRAMOS: dict[int, float] = {
    20: 9.0,
    25: 11.0,
    30: 14.0,
    35: 16.0,
    40: 18.0,
    45: 20.0,
    50: 22.0,
    55: 24.0,
    60: 26.0,
    65: 29.0,
    70: 31.0,
    75: 33.0,
    80: 35.0,
    85: 37.0,
    90: 40.0,
    95: 42.0,
    100: 44.0,
    110: 49.0,
    120: 54.0,
    125: 56.0,
}

# Catálogo de cuentas Elisa → categoría legible.
CUENTAS_ELISA: dict[str, str] = {
    "41353800": "alcohol",
    "41353801": "esencia_pura",
    "41353802": "perfumeria_preparada",
    "41353803": "splash",
    "41353804": "envases",
    "41353805": "cremas_externas",
    "41353806": "aromatizantes",
    "41353807": "bisuteria",
    "41353808": "cremas_elaboradas",
    "41353809": "accesorios_marroquineria",
    "41353810": "envases_empaques_regalo",
    "41353811": "aditivos_especiales",
    "41353814": "otros",
    "41353899": "sobrante_caja",
}

_CUENTA_CUADRE = "41353899"

# Envases conocidos (palabra completa, no substring suelto).
_ENVASES = [
    "CILINDRICO",
    "COPA",
    "TACON",
    "PERFUMERO",
    "ARABE",
    "ARABIA",
    "OVALADO",
    "OVAL",
    "CUADRADO",
    "REDONDO",
    "ATOMIZADOR",
    "SPRAY",
    "ROLON",
    "ROLLON",
    "GOTERO",
    "CANAL",
    "CANLA",
    "YARA",
    "VALENTINO",
    "COOL",
    "CREED",
    "GUITARRA",
    "OSO",
    "OSITO",
    "RELOJ",
    "MALETIN",
    "DORSO",
    "EROS",
    "POLO",
    "GLOBO",
    "CORAZON",
    "CRISTAL",
    "GENERICO",
]

# Reglas de reclasificación: si el concepto contiene estas palabras clave y
# la cuenta de origen no coincide, se mueve al grupo correcto.
# Orden importa: se evalúan en secuencia y gana la primera.
_REGLAS_RECLASIFICACION: list[tuple[re.Pattern, str]] = [
    (re.compile(r"FEROMON", re.IGNORECASE), "41353811"),            # aditivos
    (re.compile(r"\b(COLLAR|ARETE|ARETES|ANILLO|CADENA|PULSERA|TOPO|ARO|TOBILLERA|MANILLA)\b", re.IGNORECASE), "41353807"),  # bisutería
    (re.compile(r"\b(CAJA|CAJITA|STICKER|EMPAQUE|BOLSA REGALO)\b", re.IGNORECASE), "41353810"),  # empaques regalo
    (re.compile(r"COSMETIQUERA|BILLETERA|MORRAL|BOLSO", re.IGNORECASE), "41353809"),  # marroquinería
    (re.compile(r"\bSPLASH\b", re.IGNORECASE), "41353803"),         # splash
    (re.compile(r"\b(ALCOHOL|FIJADOR)\b", re.IGNORECASE), "41353800"),  # alcohol
    (re.compile(r"HUMIDIFICADOR|HUMIFICADOR|DIFUSOR", re.IGNORECASE), "41353814"),  # otros
]

# Bodega sugerida por cuenta efectiva (nombre debe existir en tabla bodegas).
BODEGA_POR_CUENTA: dict[str, str] = {
    "41353800": "Alcohol",
    "41353801": "Venta Fragancias",
    "41353802": "Venta Fragancias",
    "41353803": "Splash",
    "41353804": "Envases",
    "41353805": "Cremas",
    "41353806": "Aromatizantes",
    "41353807": "Bisuteria",
    "41353808": "Venta Fragancias",
    "41353809": "Marroquineria",
    "41353810": "Empaques",
    "41353811": "Aditivos",
    "41353814": "Otros",
}

_RE_UND = re.compile(
    r"\b(\d+)\s*(?:UND|UNID|UNIDAD|UNIDADES)\b"  # "2 UND", "3 UNID"
    r"|\bX\s*(\d+)\b"                             # "X2", "x 3"
    r"|(?<=\w\s)(\d+)x\b",                        # "2x"
    re.IGNORECASE,
)
_RE_DESCUENTO = re.compile(r"(\d+(?:[.,]\d+)?)\s*%\s*DESCUENTO", re.IGNORECASE)
# Descuento sin la palabra DESCUENTO: "20% CUMPLEAÑOS", "5 %DCTO"
_RE_PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_RE_NL = re.compile(r"(?<=\d)\s*NL\b", re.IGNORECASE)
_RE_DIGIT_SPACE = re.compile(r"(?<=\d)\s+(?=\d)")
_RE_SPACE_ML = re.compile(r"(\d)\s+ML\b", re.IGNORECASE)
_RE_SPACE_LITRO = re.compile(r"(\d)\s+(L|LT|LITRO|LITROS)\b", re.IGNORECASE)
_RE_ML = re.compile(r"(\d+(?:[.,]\d+)?)\s*ML\b", re.IGNORECASE)
_RE_LITRO = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:L|LT|LITRO|LITROS)\b", re.IGNORECASE)
_RE_ONZAS = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:OZ|ONZA|ONZAS)\b", re.IGNORECASE)
_RE_GRAMOS = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:G|GR|GRAMO|GRAMOS)\b", re.IGNORECASE)
_RE_CODIGO = re.compile(r"\b(\d+[MF])\b", re.IGNORECASE)
_RE_GENERO_ISO = re.compile(r"\b([MF])\b")
_RE_RECARGA = re.compile(r"\bRECARGA\b", re.IGNORECASE)
# "RE CARGA" / "RE-CARGA" escritos partidos
_RE_RECARGA_PARTIDA = re.compile(r"\bRE\s*[-]\s*CARGA\b|\bRE\s+CARGA\b", re.IGNORECASE)
# Código con letra duplicada: "14MM" → "14M", "20FF" → "20F"
_RE_CODIGO_DOBLE = re.compile(r"\b(\d+)(MM|FF)\b", re.IGNORECASE)
# Nota/código pegado al tamaño: "50ML0702 BARRIOS KELLY" → nota "0702 BARRIOS KELLY"
_RE_NOTA_TRAS_ML = re.compile(r"\b\d+(?:[.,]\d+)?\s*ML\s*(\d{3,}\s+.+)$", re.IGNORECASE)
_RE_OBSEQUIO = re.compile(r"\b(OBSEQUIO|REGALO|GRATIS)\b", re.IGNORECASE)
_RE_MULTI_SPACE = re.compile(r"\s+")


def gramos_esencia_por_ml(tamano_ml: int | float | None) -> float | None:
    """Busca en la tabla de mezcla. Retorna None si el tamaño no está definido."""
    if tamano_ml is None:
        return None
    try:
        clave = int(round(float(tamano_ml)))
    except (TypeError, ValueError):
        return None
    return MEZCLA_ML_A_GRAMOS.get(clave)


# Cremas elaboradas (41353808): la esencia es solo un porcentaje del
# contenido total de la crema — típicamente 15-20% (30 ml ≈ 5 g).
CREMA_ESENCIA_PCT = 0.1667  # ≈ 1/6 del volumen


def gramos_esencia_crema(tamano_ml: int | float | None) -> float | None:
    """
    Gramos de esencia para una crema elaborada: ~16.7% del tamaño en ml.
    30 ml → ~5.0 g. Retorna None si no hay tamaño.
    """
    if tamano_ml is None:
        return None
    try:
        ml = float(tamano_ml)
    except (TypeError, ValueError):
        return None
    return round(ml * CREMA_ESENCIA_PCT, 4)


def limpiar_concepto(concepto: str | None) -> dict[str, Any]:
    """
    Limpia el CONCEPTO original y extrae cantidad/descuento.

    Retorna:
        {
            "concepto_limpio": str,
            "cantidad": int,          # default 1
            "descuento_pct": float|None,
            "texto_principal": str,   # sin UND ni DESCUENTO
        }
    """
    original = "" if concepto is None else str(concepto)
    texto = original.upper().strip()
    texto = _RE_MULTI_SPACE.sub(" ", texto)

    correcciones: list[str] = []

    def _fix(pattern, repl, nombre_fix):
        nonlocal texto
        nuevo = pattern.sub(repl, texto)
        if nuevo != texto:
            correcciones.append(nombre_fix)
        texto = nuevo

    # Correcciones de tipeo conocidas
    if "CIINDRICO" in texto:
        texto = texto.replace("CIINDRICO", "CILINDRICO")
        correcciones.append("CIINDRICO→CILINDRICO")
    _fix(_RE_RECARGA_PARTIDA, "RECARGA", "RE CARGA→RECARGA")
    _fix(_RE_NL, "ML", "NL→ML")

    # Espacios sueltos entre dígitos de un código / tamaño: "4 0 M" → "40 M"
    # y luego se limpia "50 0ML" → "500ML", "30 ML" se preserva con regla ML.
    _fix(_RE_DIGIT_SPACE, "", "digitos_espaciados")
    _fix(_RE_SPACE_ML, r"\1ML", "espacio_ML")
    _fix(_RE_SPACE_LITRO, r"\1\2", "espacio_LITRO")
    # Letra de código duplicada: "14MM" → "14M", "20FF" → "20F"
    _fix(
        _RE_CODIGO_DOBLE,
        lambda m: m.group(1) + m.group(2)[0],
        "letra_codigo_duplicada",
    )
    texto = _RE_MULTI_SPACE.sub(" ", texto).strip()

    cantidad = 1
    m_und = _RE_UND.search(texto)
    if m_und:
        try:
            num = next(g for g in m_und.groups() if g is not None)
            cantidad = max(1, int(num))
        except (ValueError, StopIteration):
            cantidad = 1
        texto = _RE_UND.sub(" ", texto)

    descuento_pct = None
    m_desc = _RE_DESCUENTO.search(texto)
    if m_desc:
        try:
            descuento_pct = float(m_desc.group(1).replace(",", "."))
        except ValueError:
            descuento_pct = None
        texto = _RE_DESCUENTO.sub(" ", texto)
    else:
        # "20% CUMPLEAÑOS" / "5 %DCTO": porcentaje sin palabra DESCUENTO
        m_pct = _RE_PCT.search(texto)
        if m_pct:
            try:
                descuento_pct = float(m_pct.group(1).replace(",", "."))
            except ValueError:
                descuento_pct = None
            texto = texto[: m_pct.start()] + " " + texto[m_pct.end():]

    # Nota pegada al tamaño: "50ML0702 BARRIOS KELLY" → nota aparte
    nota = None
    m_nota = _RE_NOTA_TRAS_ML.search(texto)
    if m_nota:
        nota = _RE_MULTI_SPACE.sub(" ", m_nota.group(1)).strip()
        texto = texto[: m_nota.start(1)] + " " + texto[m_nota.end(1):]

    es_obsequio = bool(_RE_OBSEQUIO.search(texto))

    texto_principal = _RE_MULTI_SPACE.sub(" ", texto).strip(" -+/")
    concepto_limpio = _RE_MULTI_SPACE.sub(" ", original.upper().strip())
    concepto_limpio = concepto_limpio.replace("CIINDRICO", "CILINDRICO")
    concepto_limpio = _RE_RECARGA_PARTIDA.sub("RECARGA", concepto_limpio)
    concepto_limpio = _RE_NL.sub("ML", concepto_limpio)
    concepto_limpio = _RE_DIGIT_SPACE.sub("", concepto_limpio)
    concepto_limpio = _RE_SPACE_ML.sub(r"\1ML", concepto_limpio)
    concepto_limpio = _RE_SPACE_LITRO.sub(r"\1\2", concepto_limpio)
    concepto_limpio = _RE_CODIGO_DOBLE.sub(
        lambda m: m.group(1) + m.group(2)[0], concepto_limpio
    )
    concepto_limpio = _RE_MULTI_SPACE.sub(" ", concepto_limpio).strip()

    if nota:
        correcciones.append("nota_separada")

    return {
        "concepto_limpio": concepto_limpio,
        "cantidad": cantidad,
        "descuento_pct": descuento_pct,
        "texto_principal": texto_principal,
        "nota": nota,
        "es_obsequio": es_obsequio,
        "correcciones": correcciones,
        "corregido": bool(correcciones),
    }


def _to_float(s: str) -> float | None:
    try:
        return float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _extraer_tamano_ml(texto: str) -> float | None:
    m = _RE_ML.search(texto)
    if m:
        return _to_float(m.group(1))
    m = _RE_LITRO.search(texto)
    if m:
        litros = _to_float(m.group(1))
        return None if litros is None else litros * 1000.0
    return None


def _extraer_envase(texto: str) -> str | None:
    for envase in _ENVASES:
        if re.search(rf"\b{envase}\b", texto):
            return envase
    if _RE_RECARGA.search(texto):
        return "RECARGA"
    return None


def _extraer_codigos(texto: str) -> list[str]:
    """Códigos de perfume tipo 33F / 148M, en el orden de aparición."""
    return [m.group(1).upper() for m in _RE_CODIGO.finditer(texto)]


def _extraer_genero_de_codigos(codigos: list[str]) -> str | None:
    generos = {c[-1] for c in codigos if c and c[-1] in ("M", "F")}
    if len(generos) == 1:
        return next(iter(generos))
    return None


def _nombre_libre(texto: str, *quitar: str) -> str:
    """Quita tokens numéricos/unidades conocidos y deja el nombre legible."""
    limpio = texto
    for pat in (_RE_ML, _RE_LITRO, _RE_ONZAS, _RE_GRAMOS, _RE_UND, _RE_DESCUENTO):
        limpio = pat.sub(" ", limpio)
    for token in quitar:
        if token:
            limpio = re.sub(rf"\b{re.escape(token)}\b", " ", limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"[+\-/|]+", " ", limpio)
    return _RE_MULTI_SPACE.sub(" ", limpio).strip(" ,.")


def _esencia_cantidad_base(texto: str) -> dict[str, Any]:
    """
    Normaliza cantidad de esencia a gramos cuando es posible.
    onzas ≈ 28.35 g; ml de esencia se deja en ml si no hay equivalencia clara.
    """
    m = _RE_ONZAS.search(texto)
    if m:
        oz = _to_float(m.group(1))
        if oz is not None:
            return {
                "cantidad_origen": oz,
                "unidad_origen": "oz",
                "cantidad_base_g": round(oz * 28.35, 3),
            }
    m = _RE_GRAMOS.search(texto)
    if m:
        gr = _to_float(m.group(1))
        if gr is not None:
            return {
                "cantidad_origen": gr,
                "unidad_origen": "g",
                "cantidad_base_g": gr,
            }
    m = _RE_ML.search(texto)
    if m:
        ml = _to_float(m.group(1))
        if ml is not None:
            return {
                "cantidad_origen": ml,
                "unidad_origen": "ml",
                "cantidad_base_g": None,
            }
    return {}


def extraer_atributos(cuenta: str | None, concepto: str | None) -> dict[str, Any]:
    """
    Extrae atributos de producto según el código de cuenta Elisa.

    Retorna un dict con al menos:
        categoria, es_cuadre_caja, y campos específicos por cuenta.
    """
    cuenta_norm = re.sub(r"\D", "", str(cuenta or ""))
    limpio = limpiar_concepto(concepto)
    texto = limpio["texto_principal"]

    # Reclasificación por contenido: si el concepto contiene keywords de otro
    # grupo y NO tiene código de fragancia, se mueve a la cuenta correcta.
    # (ej. "FEROMONAS" en 41353801 → aditivos; "COLLAR" en 41353802 → bisutería)
    cuenta_efectiva = cuenta_norm
    reclasificado = False
    if cuenta_norm != _CUENTA_CUADRE:
        tiene_codigo = bool(_RE_CODIGO.search(texto))
        if tiene_codigo:
            # Código de fragancia + envase en una cuenta que no es de
            # perfumería (ej. "20M COPA 100ML" en alcohol) → 802.
            if (
                cuenta_norm not in ("41353802", "41353808", "41353801")
                and _extraer_envase(texto)
            ):
                cuenta_efectiva = "41353802"
                reclasificado = True
            elif cuenta_norm not in ("41353801", "41353802", "41353808"):
                cuenta_efectiva = "41353801"
                reclasificado = True
        else:
            for patron, cta_destino in _REGLAS_RECLASIFICACION:
                if patron.search(texto) and cta_destino != cuenta_norm:
                    cuenta_efectiva = cta_destino
                    reclasificado = True
                    break
        # Envase suelto sin código fuera de 804 → 804
        if not reclasificado and cuenta_norm not in ("41353804",):
            env = _extraer_envase(texto)
            if env and env != "RECARGA" and cuenta_norm in (
                "41353802", "41353808", "41353801",
            ):
                # solo reclasifica si el texto es básicamente el envase+ml
                resto = _nombre_libre(texto, env)
                if not resto:
                    cuenta_efectiva = "41353804"
                    reclasificado = True

    categoria = CUENTAS_ELISA.get(cuenta_efectiva, "desconocida")
    cuenta_norm = cuenta_efectiva

    base: dict[str, Any] = {
        "cuenta": cuenta_norm or None,
        "categoria": categoria,
        "es_cuadre_caja": cuenta_norm == _CUENTA_CUADRE,
        "concepto_limpio": limpio["concepto_limpio"],
        "cantidad": limpio["cantidad"],
        "descuento_pct": limpio["descuento_pct"],
        "nota": limpio["nota"],
        "es_obsequio": limpio["es_obsequio"],
        "correcciones": limpio["correcciones"],
        "corregido": limpio["corregido"] or reclasificado,
        "reclasificado": reclasificado,
        "cuenta_original": cuenta_efectiva if not reclasificado else re.sub(r"\D", "", str(cuenta or "")),
        "bodega_sugerida": BODEGA_POR_CUENTA.get(cuenta_norm),
    }

    if base["es_cuadre_caja"]:
        # 41353899 = SOBRANTE de caja: no es producto.
        return base

    if cuenta_norm == "41353800":
        # Alcohol: tamaño ml/litro
        base["tamano_ml"] = _extraer_tamano_ml(texto)
        base["nombre"] = _nombre_libre(texto) or "ALCOHOL"
        return base

    if cuenta_norm == "41353801":
        # Esencia pura: código + cantidad (onzas/gr/ml → base en g si aplica)
        codigos = _extraer_codigos(texto)
        base["codigos"] = codigos
        base["codigo"] = codigos[0] if len(codigos) == 1 else None
        base.update(_esencia_cantidad_base(texto))
        base["nombre"] = _nombre_libre(texto, *codigos) or None
        return base

    if cuenta_norm in ("41353802", "41353808"):
        # Perfumería preparada / cremas elaboradas
        codigos = _extraer_codigos(texto)
        envase = _extraer_envase(texto)
        tamano_ml = _extraer_tamano_ml(texto)
        base["codigos"] = codigos
        base["codigo"] = codigos[0] if len(codigos) == 1 else None
        base["es_combo"] = len(codigos) > 1
        base["envase"] = envase
        base["tamano_ml"] = tamano_ml
        base["genero"] = _extraer_genero_de_codigos(codigos)
        if cuenta_norm == "41353808":
            # Cremas: la esencia es ~15-20% del contenido, no la mezcla full.
            base["gramos_esencia_total"] = gramos_esencia_crema(tamano_ml)
            base["regla_esencia"] = "crema_pct_16.7"
        else:
            base["gramos_esencia_total"] = gramos_esencia_por_ml(tamano_ml)
            base["regla_esencia"] = "mezcla_perfume"
        # No repartir esencia entre códigos aquí (Fase 4).
        base["nombre"] = _nombre_libre(texto, *(codigos + ([envase] if envase else []))) or None
        return base

    if cuenta_norm == "41353803":
        # Splash: nombre libre + género
        codigos = _extraer_codigos(texto)
        genero = _extraer_genero_de_codigos(codigos)
        if genero is None:
            m = _RE_GENERO_ISO.search(texto)
            genero = m.group(1).upper() if m else None
        base["codigos"] = codigos
        base["genero"] = genero
        base["nombre"] = _nombre_libre(texto, *codigos, "M", "F", "SPLASH") or texto or None
        base["tamano_ml"] = _extraer_tamano_ml(texto)
        return base

    if cuenta_norm == "41353804":
        # Envases: tipo + tamaño
        envase = _extraer_envase(texto)
        base["envase"] = envase
        base["tamano_ml"] = _extraer_tamano_ml(texto)
        base["nombre"] = _nombre_libre(texto, envase) or envase or texto or None
        return base

    if cuenta_norm == "41353806":
        # Aromatizantes: nombre + tamaño (ml/litro). Sin tabla de mezcla.
        base["tamano_ml"] = _extraer_tamano_ml(texto)
        base["nombre"] = _nombre_libre(texto) or texto or None
        return base

    if cuenta_norm in ("41353805", "41353807", "41353809", "41353810", "41353811", "41353814"):
        # Nombre libre (+ cantidad ya viene de limpiar_concepto)
        base["nombre"] = _nombre_libre(texto) or texto or None
        base["tamano_ml"] = _extraer_tamano_ml(texto)
        return base

    # Cuenta desconocida: al menos dejar el texto limpio
    base["nombre"] = texto or None
    base["tamano_ml"] = _extraer_tamano_ml(texto)
    base["codigos"] = _extraer_codigos(texto)
    base["envase"] = _extraer_envase(texto)
    return base


def parsear_fila_elisa(cuenta: str | None, concepto: str | None) -> dict[str, Any]:
    """
    Punto de entrada de Fase 1 para una fila del Excel.

    Combina limpieza + extracción de atributos en un solo resultado listo
    para persistir en ventas_import_raw.
    """
    limpio = limpiar_concepto(concepto)
    attrs = extraer_atributos(cuenta, concepto)
    return {
        "concepto_limpio": limpio["concepto_limpio"],
        "cantidad": limpio["cantidad"],
        "descuento_pct": limpio["descuento_pct"],
        "atributos": attrs,
        "es_cuadre_caja": bool(attrs.get("es_cuadre_caja")),
    }
