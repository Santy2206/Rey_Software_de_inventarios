"""
Utilidades de parseo y transformación de datos para reportes.

Convierte los resultados crudos de Supabase en estructuras
limpias y listas para ser usadas por los generadores.

Reglas:
    - Entrada: dicts o listas crudas de respuestas de Supabase.
    - Salida: dicts normalizados o instancias de dataclasses.
    - SIN importaciones de Flet, SIN llamadas a la base de datos
      — solo transformación de datos.
"""
