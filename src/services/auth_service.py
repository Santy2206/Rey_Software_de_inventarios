from src.core.supabase_client import supabase


class AuthService:
    @staticmethod
    def login(username_typed, password_typed):
        # 1. Start a log in the console so we see the action
        print(f"--- Intento de login: {username_typed} ---")

        try:
            # 2. Lookup the email using the 'username' column
            # Note: Using .single() is important because usernames should be unique
            res = (
                supabase.table("usuarios")
                .select("email, rol")
                .eq(
                    "username", username_typed
                )  # Verifica que sea 'username' y no 'nombre'
                .single()
                .execute()
            )

            # If the user doesn't exist in the 'usuarios' table
            if not res.data:
                print("❌ Usuario no encontrado en la tabla 'usuarios'")
                return {"success": False, "message": "El nombre de usuario no existe"}

            user_email = res.data["email"]
            user_role = res.data["rol"]
            print(f"✅ Email encontrado: {user_email}. Autenticando...")

            # 3. Authenticate with Supabase Auth
            auth_res = supabase.auth.sign_in_with_password(
                {"email": user_email, "password": password_typed}
            )

            print("🎉 Login exitoso!")
            return {
                "success": True,
                "message": f"Bienvenido {username_typed}",
                "rol": user_role,
            }

        except Exception as e:
            # This will catch wrong passwords OR connection issues
            error_msg = str(e)
            print(f"🔥 Error en AuthService: {error_msg}")

            # Simple user-friendly messages
            if "Invalid login credentials" in error_msg:
                return {"success": False, "message": "Contraseña incorrecta"}
            return {"success": False, "message": f"Error: {error_msg}"}
