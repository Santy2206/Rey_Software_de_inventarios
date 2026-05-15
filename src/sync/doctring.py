"""
Capa de sincronización local ↔ nube.

Gestiona la sincronización en segundo plano entre la base de datos
PostgreSQL local y la instancia en la nube de Supabase.

Responsabilidades:
    - Detectar cambios locales pendientes de sincronizar.
    - Enviar registros locales a Supabase.
    - Descargar actualizaciones remotas cuando se recupera la conexión.

Reglas:
    - Funciona de forma independiente a la interfaz.
    - SIN importaciones de Flet.
    - Debe operar sin conexión a internet de forma segura
      (fallo gracioso y lógica de reintento).
"""
