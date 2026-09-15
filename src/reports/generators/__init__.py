"""
Módulos de generación de reportes.

Cada archivo de este paquete es responsable de construir
un tipo de reporte (ej: valor del inventario, resumen de ventas,
movimientos de stock).

Convenciones:
    - Cada generador recibe datos procesados (listas de dicts u objetos).
    - Retorna un resultado estructurado (bytes PDF, ruta de Excel o dict).
    - SIN importaciones de Flet — los generadores son independientes de la UI.
"""
