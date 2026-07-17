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
                print(" Usuario no encontrado en la tabla 'usuarios'")
                return {
                    "success": False,
                    "message": "El nombre de usuario no existe",
                }

            user_data = res.data[0]

            user_email = user_data["email"]
            user_role = user_data["rol"]

            print(f" Email encontrado: {user_email}. Autenticando...")

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

            print(f" Error en AuthService: {error_msg}")

            if "Invalid login credentials" in error_msg:
                return {
                    "success": False,
                    "message": "Contraseña incorrecta",
                }

            return {
                "success": False,
                "message": f"Error: {error_msg}",
            }


def get_usuario_id():
    """
    Función temporal para simular la sesión de un usuario.
    Devuelve un ID por defecto para que la interfaz no falle.
    """
    return "admin-123"
