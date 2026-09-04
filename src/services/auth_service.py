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
import json
import time
from pathlib import Path

from src.core.local_db import run_query
from src.services.bitacora_service import BitacoraService

_current_usuario_id = None
_current_usuario_rol = None
_current_usuario_name = None

# Sesión local para conservar login al cambiar de modo (navegador <-> escritorio)
_SESSION_FILE = Path(__file__).resolve().parents[2] / ".rey_session.json"
_SESSION_TTL_SECONDS = 12 * 60 * 60  # 12 horas


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
        global _current_usuario_id, _current_usuario_rol

        print(f"--- Intento de login: {username_typed} ---")

        try:
            rows = run_query(
                "SELECT id, name, email, rol, password_hash FROM usuarios WHERE name = %s",
                (username_typed,),
            )

            if not rows:
                print("Usuario no encontrado en la tabla 'usuarios'")
                return {
                    "success": False,
                    "message": "El nombre de usuario no existe",
                }

            user_data = rows[0]

            if not _verificar_password(password_typed, user_data["password_hash"]):
                print("Contraseña incorrecta")
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
            _current_usuario_rol = user_data["rol"]
            _current_usuario_name = user_data["name"]
            AuthService._guardar_sesion(
                user_id=user_data["id"],
                rol=user_data["rol"],
                name=user_data["name"],
            )

            BitacoraService.registrar(
                user_data["id"],
                "LOGIN",
                {
                    "descripcion": f"Login exitoso: {username_typed}",
                    "rol": user_data["rol"],
                },
            )

            print("Login exitoso!")
            return {
                "success": True,
                "message": f"Bienvenido {username_typed}",
                "id": user_data["id"],
                "rol": user_data["rol"],
                "name": user_data["name"],
            }

        except Exception as e:
            error_msg = str(e)
            print(f"Error en AuthService: {error_msg}")
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
        try:
            if _current_usuario_id is None:
                AuthService.restore_session()
            return _current_usuario_id
        except Exception as e:
            print(f"Error en AuthService.get_usuario_id: {e}")
            return None

    @staticmethod
    def get_rol():
        """Retorna el rol del usuario autenticado en la sesión actual."""
        if _current_usuario_rol is None:
            AuthService.restore_session()
        return _current_usuario_rol

    @staticmethod
    def get_name():
        """Retorna el nombre del usuario autenticado en la sesión actual."""
        if _current_usuario_name is None:
            AuthService.restore_session()
        return _current_usuario_name

    @staticmethod
    def logout():
        """Cierra la sesión en memoria y elimina el archivo local."""
        global _current_usuario_id, _current_usuario_rol, _current_usuario_name
        _current_usuario_id = None
        _current_usuario_rol = None
        _current_usuario_name = None
        AuthService._borrar_sesion()

    @staticmethod
    def restore_session():
        """
        Restaura la sesión desde el archivo local, si sigue vigente.

        Retorna:
            dict | None: {'id', 'rol', 'name'} si hay sesión válida; None si no.
        """
        global _current_usuario_id, _current_usuario_rol, _current_usuario_name
        data = AuthService._leer_sesion()
        if not data:
            return None

        usuario_id = data.get("id")
        if not usuario_id:
            AuthService._borrar_sesion()
            return None

        # Verificar que el usuario sigue existiendo en la BD local
        row = run_query(
            "SELECT id, name, rol FROM usuarios WHERE id = %s",
            (usuario_id,),
            fetch_one=True,
        )
        if not row:
            AuthService._borrar_sesion()
            return None

        _current_usuario_id = row["id"]
        _current_usuario_rol = row["rol"]
        _current_usuario_name = row["name"]
        return {
            "id": row["id"],
            "rol": row["rol"],
            "name": row["name"],
        }

    @staticmethod
    def _guardar_sesion(user_id: str, rol: str, name: str):
        payload = {
            "id": user_id,
            "rol": rol,
            "name": name,
            "saved_at": time.time(),
        }
        try:
            _SESSION_FILE.write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"No se pudo guardar la sesión local: {e}")

    @staticmethod
    def _leer_sesion():
        try:
            if not _SESSION_FILE.exists():
                return None
            data = json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
            saved_at = float(data.get("saved_at") or 0)
            if time.time() - saved_at > _SESSION_TTL_SECONDS:
                AuthService._borrar_sesion()
                return None
            return data
        except Exception:
            AuthService._borrar_sesion()
            return None

    @staticmethod
    def _borrar_sesion():
        try:
            if _SESSION_FILE.exists():
                _SESSION_FILE.unlink()
        except Exception:
            pass
