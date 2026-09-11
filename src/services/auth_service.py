"""
Servicio de autenticación.

El login es contra Supabase Auth. Supabase es el encargado de gestionar
usuarios, contraseñas y tokens. La tabla local 'usuarios' se usa solo para
obtener el id, nombre y rol del usuario autenticado (se crea o sincroniza
automáticamente si no existe).

Retorna:
    dict: {
        "success" (bool): Si el login fue exitoso o no.
        "message" (str):  Mensaje legible para mostrar al usuario.
        "rol"     (str):  Rol del usuario — solo presente si success es True.
    }

Reglas:
    - SIN importaciones de Flet.
    - Todos los errores se capturan internamente y se retornan diccionarios.
"""

import json
import time
from pathlib import Path

from src.core.local_db import run_query
from src.core.supabase_client import supabase
from src.services.bitacora_service import BitacoraService

_current_usuario_id = None
_current_usuario_rol = None
_current_usuario_name = None

# Sesión local para conservar login al cambiar de modo (navegador <-> escritorio)
_SESSION_FILE = Path(__file__).resolve().parents[2] / ".rey_session.json"
_SESSION_TTL_SECONDS = 12 * 60 * 60  # 12 horas


def _sincronizar_usuarios_desde_supabase():
    """
    Trae los usuarios de Supabase y los mantiene en la tabla local.
    Así, usuarios creados/modificados en Supabase son visibles inmediatamente.
    """
    try:
        resp = supabase.table("usuarios").select("*").execute()
        if not resp or not getattr(resp, "data", None):
            return
        for u in resp.data:
            if not u.get("id") or not u.get("email"):
                continue
            existing = run_query(
                "SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s)",
                (u["email"],),
                fetch_one=True,
            )
            if existing:
                run_query(
                    """
                    UPDATE usuarios
                    SET name = %s, rol = %s, password_hash = %s
                    WHERE LOWER(email) = LOWER(%s)
                    """,
                    (
                        u.get("name") or u["email"],
                        u.get("rol") or "vendedor",
                        u.get("password_hash"),
                        u["email"],
                    ),
                )
            else:
                run_query(
                    """
                    INSERT INTO usuarios (id, name, email, rol, password_hash)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        email = EXCLUDED.email,
                        rol = EXCLUDED.rol,
                        password_hash = EXCLUDED.password_hash
                    """,
                    (
                        u["id"],
                        u.get("name") or u["email"],
                        u.get("email"),
                        u.get("rol") or "vendedor",
                        u.get("password_hash"),
                    ),
                )
    except Exception as e:
        print(f"No se pudieron sincronizar usuarios: {e}")


def _localizar_por_email(email: str):
    """Busca o crea un usuario local a partir del email de Supabase."""
    row = run_query(
        "SELECT id, name, email, rol FROM usuarios WHERE LOWER(email) = LOWER(%s)",
        (email,),
        fetch_one=True,
    )
    if row:
        return dict(row)
    # Si no existe localmente, creamos un registro básico para poder operar.
    return run_query(
        """
        INSERT INTO usuarios (name, email, rol, password_hash, dirty)
        VALUES (%s, %s, %s, %s, true)
        RETURNING id, name, email, rol
        """,
        (email, email, "vendedor", "supabase-managed"),
        fetch_one=True,
    )


class AuthService:
    @staticmethod
    def login(username_typed, password_typed):
        global _current_usuario_id, _current_usuario_rol, _current_usuario_name

        print(f"--- Intento de login: {username_typed} ---")

        if not password_typed or not str(password_typed).strip():
            return {"success": False, "message": "Ingrese la contraseña"}

        # Traer usuarios creados/modificados en Supabase
        _sincronizar_usuarios_desde_supabase()

        # El usuario puede escribir email o nombre local. Si no tiene '@',
        # buscamos el email asociado en la tabla local.
        email = str(username_typed).strip()
        if "@" not in email:
            row = run_query(
                "SELECT email FROM usuarios WHERE name = %s LIMIT 1",
                (email,),
                fetch_one=True,
            )
            if not row or not row.get("email"):
                return {
                    "success": False,
                    "message": "Usuario no encontrado",
                }
            email = row["email"]

        try:
            auth = supabase.auth.sign_in_with_password(
                {"email": email, "password": str(password_typed)}
            )
            if not auth or not getattr(auth, "user", None):
                return {"success": False, "message": "Contraseña incorrecta"}

            user_email = auth.user.email or email
            local = _localizar_por_email(user_email)
            if not local:
                return {
                    "success": False,
                    "message": "No se pudo sincronizar el usuario local",
                }

            _current_usuario_id = local["id"]
            _current_usuario_rol = local["rol"]
            _current_usuario_name = local["name"]
            AuthService._guardar_sesion(
                user_id=local["id"],
                rol=local["rol"],
                name=local["name"],
                email=local.get("email") or user_email,
            )

            print("Login exitoso!")
            return {
                "success": True,
                "message": f"Bienvenido {local['name']}",
                "id": local["id"],
                "rol": local["rol"],
                "name": local["name"],
            }

        except Exception as e:
            error_msg = str(e)
            print(f"Error en AuthService: {error_msg}")
            if "Invalid login" in error_msg or "invalid" in error_msg.lower():
                return {"success": False, "message": "Correo o contraseña incorrectos"}
            if "network" in error_msg.lower() or "connection" in error_msg.lower():
                return {
                    "success": False,
                    "message": "Sin conexión con Supabase. Verifique internet.",
                }
            return {"success": False, "message": f"Error: {error_msg}"}

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
    def verificar_password_sesion(password_typed: str):
        """
        Re-autentica contra Supabase con la contraseña ingresada.

        Útil antes de acciones sensibles (editar/eliminar).

        Retorna:
            dict: {"success": bool, "message": str}
        """
        try:
            sess = AuthService._leer_sesion()
            if not sess or not sess.get("email"):
                return {
                    "success": False,
                    "message": "No hay sesión activa. Inicie sesión de nuevo.",
                }

            if not password_typed or not str(password_typed).strip():
                return {
                    "success": False,
                    "message": "Debe ingresar su contraseña",
                }

            supabase.auth.sign_in_with_password(
                {"email": sess["email"], "password": str(password_typed).strip()}
            )
            return {"success": True, "message": "Contraseña verificada"}
        except Exception as e:
            print(f"Error en AuthService.verificar_password_sesion: {e}")
            return {"success": False, "message": "Contraseña incorrecta"}

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
        """Cierra la sesión en Supabase y en memoria."""
        global _current_usuario_id, _current_usuario_rol, _current_usuario_name
        _current_usuario_id = None
        _current_usuario_rol = None
        _current_usuario_name = None
        try:
            supabase.auth.sign_out()
        except Exception as e:
            print(f"No se pudo cerrar sesión en Supabase: {e}")
        AuthService._borrar_sesion()

    @staticmethod
    def restore_session():
        """
        Restaura la sesión desde Supabase (online) o desde el archivo local.

        Retorna:
            dict | None: {'id', 'rol', 'name'} si hay sesión válida; None si no.
        """
        global _current_usuario_id, _current_usuario_rol, _current_usuario_name

        # Actualizar usuarios locales desde Supabase
        _sincronizar_usuarios_desde_supabase()

        # 1) Intentar validar sesión activa en Supabase
        try:
            user_resp = supabase.auth.get_user()
            user = user_resp.user if user_resp else None
            if user and user.email:
                local = _localizar_por_email(user.email)
                if local:
                    _current_usuario_id = local["id"]
                    _current_usuario_rol = local["rol"]
                    _current_usuario_name = local["name"]
                    AuthService._guardar_sesion(
                        user_id=local["id"],
                        rol=local["rol"],
                        name=local["name"],
                        email=user.email,
                    )
                    return {
                        "id": local["id"],
                        "rol": local["rol"],
                        "name": local["name"],
                    }
        except Exception as e:
            print(f"No se pudo restaurar sesión en Supabase: {e}")

        # 2) Fallback offline por archivo local
        data = AuthService._leer_sesion()
        if not data:
            return None

        usuario_id = data.get("id")
        if not usuario_id:
            AuthService._borrar_sesion()
            return None

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
    def _guardar_sesion(user_id: str, rol: str, name: str, email: str = ""):
        payload = {
            "id": user_id,
            "rol": rol,
            "name": name,
            "email": email,
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
