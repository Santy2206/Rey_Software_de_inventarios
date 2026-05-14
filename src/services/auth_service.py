from core.supabase_client import supabase


class AuthService:
    @staticmethod
    def login(username, password):
        # 1. Validaciones básicas de texto
        if not username or not password:
            return {"success": False, "message": "Campos obligatorios vacíos"}

        # 2. Consulta a base de datos
        try:
            res = (
                supabase.table("usuarios")
                .select("*")
                .eq("nombre", username)
                .eq("password", password)
                .execute()
            )
            if len(res.data) > 0:
                return {"success": True, "message": "¡Bienvenido!", "user": res.data[0]}
            return {"success": False, "message": "Usuario o clave incorrectos"}
        except Exception as e:
            return {"success": False, "message": f"Error de conexión: {str(e)}"}
