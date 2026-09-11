"""
Servicio de Usuarios — base de datos local.

Gestiona la consulta de usuarios y el cambio de rol. El cambio de rol
es una acción sensible: queda registrada en la bitácora (CAMBIO_ROL).

Tabla:
    usuarios (id, name, email, rol, creado_en, password_hash)

Mismo contrato que el resto de servicios:
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - SIN importaciones de Flet — solo lógica pura
"""

from src.core.local_db import run_query
from src.core.supabase_client import supabase
from src.services.auth_service import AuthService
from src.services.bitacora_service import BitacoraService

ROLES_VALIDOS = ["administrador", "vendedor", "bodeguero", "empleado"]


def _registrar_bitacora_usuarios(
    accion: str, entidad_id: str, detalle: str
):
    """Registra en bitácora sin afectar la operación principal."""
    try:
        usuario_sesion = AuthService.get_usuario_id()
        if usuario_sesion:
            BitacoraService.registrar(
                usuario_sesion,
                accion,
                entidad="usuario",
                entidad_id=entidad_id,
                detalle=detalle,
            )
    except Exception as e:
        print(f" Error al registrar bitácora de usuario: {e}")


class UsuariosService:

    @staticmethod
    def get_all():
        """Trae todos los usuarios ordenados por nombre."""
        print("--- Trayendo todos los usuarios ---")
        try:
            data = run_query(
                "SELECT id, name, email, rol, creado_en "
                "FROM usuarios ORDER BY name"
            )

            if not data:
                return {
                    "success": True,
                    "message": "No hay usuarios registrados",
                    "data": [],
                }

            print(f" Se encontraron {len(data)} usuario(s)")
            return {"success": True, "message": "Usuarios obtenidos", "data": data}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en UsuariosService.get_all: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener usuarios: {error_msg}",
                "data": [],
            }

    @staticmethod
    def create(nombre: str, email: str, password: str, rol: str):
        """
        Crea un usuario en Supabase Auth y lo refleja en la tabla local.

        El password se maneja por Supabase Auth; en local solo se guarda
        un marcador 'supabase-managed'.
        """
        print(f"--- Creando usuario: {email} ---")
        if not AuthService.es_administrador():
            return {"success": False, "message": "No tiene permisos para crear usuarios"}
        try:
            nombre_limpio = (nombre or "").strip()
            email_limpio = (email or "").strip().lower()
            password_limpio = (password or "").strip()
            rol_limpio = (rol or "").strip()

            if not nombre_limpio:
                return {"success": False, "message": "El nombre es obligatorio"}
            if not email_limpio or "@" not in email_limpio:
                return {"success": False, "message": "Ingrese un correo válido"}
            if not password_limpio or len(password_limpio) < 6:
                return {
                    "success": False,
                    "message": "La contraseña debe tener al menos 6 caracteres",
                }
            if rol_limpio not in ROLES_VALIDOS:
                return {
                    "success": False,
                    "message": f"Rol no válido. Válidos: {', '.join(ROLES_VALIDOS)}",
                }

            existente = run_query(
                "SELECT id FROM usuarios WHERE LOWER(email) = %s",
                (email_limpio,),
                fetch_one=True,
            )
            if existente:
                return {
                    "success": False,
                    "message": f"Ya existe un usuario con el correo '{email_limpio}'",
                }

            # Crear el usuario en Supabase Auth
            auth = supabase.auth.sign_up(
                {"email": email_limpio, "password": password_limpio}
            )
            if not auth or not getattr(auth, "user", None):
                return {
                    "success": False,
                    "message": "No se pudo crear el usuario en Supabase Auth",
                }

            user_id = str(auth.user.id)

            # Crear el reflejo local
            run_query(
                """
                INSERT INTO usuarios (id, name, email, rol, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, nombre_limpio, email_limpio, rol_limpio, "supabase-managed"),
            )

            _registrar_bitacora_usuarios(
                "CREACION_USUARIO",
                entidad_id=user_id,
                detalle=f"Usuario creado: {nombre_limpio} ({email_limpio}) con rol {rol_limpio}",
            )

            print(f" Usuario '{nombre_limpio}' creado con éxito")
            return {
                "success": True,
                "message": f"Usuario '{nombre_limpio}' creado con éxito",
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en UsuariosService.create: {error_msg}")
            return {"success": False, "message": f"Error al crear usuario: {error_msg}"}

    @staticmethod
    def cambiar_rol(usuario_id: str, nuevo_rol: str):
        """
        Cambia el rol de un usuario.

        Parámetros:
            usuario_id: id del usuario a modificar
            nuevo_rol:  debe estar en ROLES_VALIDOS

        Reglas:
            - Solo administradores.
            - No se puede cambiar el rol del usuario de la sesión actual
              (evita que un administrador se quite el acceso a sí mismo).
            - Registra CAMBIO_ROL en la bitácora.
        """
        print(f"--- Cambiando rol del usuario {usuario_id} a '{nuevo_rol}' ---")
        if not AuthService.es_administrador():
            return {"success": False, "message": "No tiene permisos para cambiar roles"}
        try:
            if nuevo_rol not in ROLES_VALIDOS:
                return {
                    "success": False,
                    "message": (
                        f"Rol no válido: {nuevo_rol}. "
                        f"Válidos: {', '.join(ROLES_VALIDOS)}"
                    ),
                }

            if str(usuario_id) == str(AuthService.get_usuario_id()):
                return {
                    "success": False,
                    "message": "No puedes cambiar tu propio rol",
                }

            actual = run_query(
                "SELECT id, name, rol FROM usuarios WHERE id = %s",
                (usuario_id,),
                fetch_one=True,
            )
            if not actual:
                return {"success": False, "message": "Usuario no encontrado"}

            if actual["rol"] == nuevo_rol:
                return {
                    "success": False,
                    "message": f"El usuario ya tiene el rol '{nuevo_rol}'",
                }

            run_query(
                "UPDATE usuarios SET rol = %s WHERE id = %s",
                (nuevo_rol, usuario_id),
            )

            _registrar_bitacora_usuarios(
                "CAMBIO_ROL",
                entidad_id=usuario_id,
                detalle=(
                    f"Rol de '{actual['name']}': "
                    f"{actual['rol']} → {nuevo_rol}"
                ),
            )

            print(f" Rol de '{actual['name']}' actualizado a '{nuevo_rol}'")
            return {
                "success": True,
                "message": f"Rol de '{actual['name']}' cambiado a '{nuevo_rol}'",
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en UsuariosService.cambiar_rol: {error_msg}")
            return {
                "success": False,
                "message": f"Error al cambiar el rol: {error_msg}",
            }
