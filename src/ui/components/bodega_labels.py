"""
Etiqueta de bodega con sus cuentas Elisa para dropdowns.

- Todas las bodegas muestran "Nombre (cuentas)" si tienen cuentas_elisa.
"""


def label_bodega(bodega: dict) -> str:
    nombre = (bodega.get("nombre") or "—").strip()
    cuentas = (bodega.get("cuentas_elisa") or "").strip()
    return f"{nombre} ({cuentas})" if cuentas else nombre
