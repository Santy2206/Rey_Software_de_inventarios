"""
Servicio de autenticación.

Maneja la lógica de inicio de sesión contra PostgreSQL local:
1. Busca el usuario por el campo 'name' en la tabla 'usuarios'.
2. Verifica la contraseña contra 'password_hash'.
3. Devuelve el resultado en el contrato habitual — nunca lanza excepciones a la UI.

Retorna:
    dict: {
        "success" (bool): Si el login fue exitoso o no.
        "message" (str):  Mensaje legible para mostrar al usuario.
        "rol"     (str):  Rol del usuario — solo presente si success es True.
    }

Reglas:
    - SIN importaciones de Flet.
    - Todos los errores se capturan internamente y se retornan como diccionarios.
"""

import hashlib

from src.core.local_db import run_query
from src.services.bitacora_service import BitacoraService

_current_usuario_id = None


def _verificar_password(plain: str, hashed: str) -> bool:
    """
    Verifica una contraseña candidata contra el hash almacenado.

    Soporta:
      - Hashes SHA-256 hex (común en migraciones locales).
      - Comparación directa si aún se almacena en texto plano (NO recomendado).

    Si en el futuro se adopta bcrypt/argon2, reemplazar esta función por
    la librería de hashing correspondiente.
    """
    if not plain or not hashed:
        return False
    if plain == hashed:
        return True
    sha = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    return sha == hashed


class AuthService:
    @staticmethod
    def login(username_typed, password_typed):
        global _current_usuario_id

        print(f"--- Intento de login: {username_typed} ---")

        try:
            rows = run_query(
                "SELECT id, name, email, rol, password_hash FROM usuarios WHERE name = %s",
                (username_typed,),
            )

            if not rows:
                print("❌ Usuario no encontrado en la tabla 'usuarios'")
                return {
                    "success": False,
                    "message": "El nombre de usuario no existe",
                }

            user_data = rows[0]

            if not _verificar_password(password_typed, user_data["password_hash"]):
                print("❌ Contraseña incorrecta")
                BitacoraService.registrar(
                    user_data["id"],
                    "LOGIN_FALLIDO",
                    {
                        "descripcion": f"Intento fallido de login: {username_typed}",
                        "motivo": "Contraseña incorrecta",
                    },
                )
                return {
                    "success": False,
                    "message": "Contraseña incorrecta",
                }

            _current_usuario_id = user_data["id"]

            BitacoraService.registrar(
                user_data["id"],
                "LOGIN",
                {
                    "descripcion": f"Login exitoso: {username_typed}",
                    "rol": user_data["rol"],
                },
            )

            print("🎉 Login exitoso!")
            return {
                "success": True,
                "message": f"Bienvenido {username_typed}",
                "id": user_data["id"],
                "rol": user_data["rol"],
            }

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en AuthService: {error_msg}")
            return {
                "success": False,
                "message": f"Error: {error_msg}",
            }

    @staticmethod
    def get_usuario_id():
        """
        Retorna el id del usuario autenticado en la sesión local.

        El id corresponde a la llave primaria de la tabla 'usuarios' en la
        base de datos local. Se almacena en memoria después de un login
        exitoso, por lo que no depende de Supabase Auth.

        Retorna:
            str | None: el id del usuario autenticado, o None si no hay
            sesión activa o si ocurre un error.
        """
        print("--- Buscando id del usuario autenticado ---")
        try:
            if _current_usuario_id is None:
                print("⚠️ No hay sesión activa en la base de datos local")
                return None

            print(f"✅ Usuario autenticado: {_current_usuario_id}")
            return _current_usuario_id

        except Exception as e:
            error_msg = str(e)
            print(f"🔥 Error en AuthService.get_usuario_id: {error_msg}")
            return None
