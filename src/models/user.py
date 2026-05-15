"""
Modelo / esquema de datos del usuario.

Define la estructura de un registro de usuario tal como
lo devuelve Supabase. Se usa para tipado y validación de datos
en los servicios y vistas.

Campos:
    id       (str)  : Identificador único (UUID de Supabase Auth).
    username (str)  : Nombre de usuario utilizado para iniciar sesión.
    email    (str)  : Correo electrónico vinculado a Supabase Auth.
    rol      (str)  : Nivel de acceso — 'administrador' o 'vendedor'.

Reglas:
    - Sin importaciones de Flet ni de Supabase — solo Python puro.
"""
