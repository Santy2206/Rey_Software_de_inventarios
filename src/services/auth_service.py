"""
Servicio de autenticación.

Maneja toda la lógica de inicio de sesión contra Supabase:
1. Busca el correo del usuario por su nombre de usuario en la tabla 'usuarios'.
2. Autentica mediante Supabase Auth (sign_in_with_password).
3. Devuelve un diccionario con el resultado — nunca lanza excepciones a la UI.

Retorna:
    dict: {
        "success" (bool)   : Si el login fue exitoso o no.
        "message" (str)    : Mensaje legible para mostrar al usuario.
        "rol"     (str)    : Rol del usuario — solo presente si success es True.
    }

Reglas:
    - SIN importaciones de Flet.
    - SIN interacción directa con la página ni los controles.
    - Todos los errores se capturan internamente y se retornan como diccionarios.
"""

from src.core.supabase_client import supabase


class AuthService:
    @staticmethod
    def login(username_typed, password_typed):

        print(f"--- Intento de login: {username_typed} ---")

        try:

            res = (
                supabase.table("usuarios")
                .select("email, rol")
                .eq("username", username_typed)
                .execute()
            )

            print("DEBUG:", res)

            if not res or not hasattr(res, "data"):
                return {
                    "success": False,
                    "message": "Error consultando Supabase",
                }

            if not res.data or len(res.data) == 0:
                print("❌ Usuario no encontrado en la tabla 'usuarios'")
                return {
                    "success": False,
                    "message": "El nombre de usuario no existe",
                }

            user_data = res.data[0]

            user_email = user_data["email"]
            user_role = user_data["rol"]

            print(f"✅ Email encontrado: {user_email}. Autenticando...")

            auth_res = supabase.auth.sign_in_with_password(
                {
                    "email": user_email,
                    "password": password_typed,
                }
            )

            print("🎉 Login exitoso!")

            return {
                "success": True,
                "message": f"Bienvenido {username_typed}",
                "rol": user_role,
            }

        except Exception as e:

            error_msg = str(e)

            print(f"🔥 Error en AuthService: {error_msg}")

            if "Invalid login credentials" in error_msg:
                return {
                    "success": False,
                    "message": "Contraseña incorrecta",
                }

            return {
                "success": False,
                "message": f"Error: {error_msg}",
            }

    @staticmethod
    def get_usuario_id():
        """
        Retorna el id del usuario actualmente autenticado en Supabase Auth.

        Se usa en vistas como movimientos_view.py para saber quién está
        registrando una acción (ej: usuario_id en un movimiento de inventario).

        ⚠️ IMPORTANTE — verificar contra el esquema:
        Este id es el UUID de Supabase Auth (auth.users), NO necesariamente
        el mismo 'id' que usas como llave primaria en tu tabla 'usuarios'.
        AuthService.login() busca el usuario por 'username' en 'usuarios' pero
        nunca guarda ese id — solo trae 'email' y 'rol'. Si 'usuarios.id' es
        una columna independiente (no igual al UUID de auth.users), este
        método va a devolver un id que no coincide con tu llave foránea en
        'movimientos.usuario_id', y el insert puede fallar o insertar un id
        inválido. Antes de usar esto en producción, confirma si 'usuarios.id'
        está definido igual al UUID de auth.users (patrón común en Supabase)
        o si es una secuencia/uuid propia.

        Retorna:
            str | None: el UUID del usuario autenticado, o None si no hay
            sesión activa o si ocurre un error.
        """
        print("--- Buscando id del usuario autenticado ---")
        try:
            session = supabase.auth.get_session()

            if not session or not session.user:
                print("⚠️ No hay sesión activa en Supabase Auth")
                return None

            usuario_id = session.user.id
            print(f"✅ Usuario autenticado: {usuario_id}")
            return usuario_id

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en AuthService.get_usuario_id: {error_msg}")
            return None
