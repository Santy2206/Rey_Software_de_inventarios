"""
Vista de la pantalla de inicio de sesión.

Retorna un Container de Flet con:
- Campos de texto para usuario y contraseña.
- Botón 'INGRESAR' que dispara el callback on_login.

Parámetros:
    on_login (callable): Función que se llama con (usuario: str, contraseña: str)
                        cuando el usuario hace clic en el botón.

Retorna:
    ft.Container: La tarjeta de login completa, lista para agregar a la página.

Reglas:
    - SIN lógica de negocio — solo diseño de interfaz.
    - SIN llamadas directas a Supabase o AuthService.
    - SIN acceso al objeto `page` — se comunica solo mediante callbacks.
"""

import flet as ft


def LoginView(on_login):
    usuario_input = ft.TextField(
        hint_text="Usuario",
        border_radius=30,
        filled=True,
        bgcolor="#f5e6d3",
        border_color="transparent",
        cursor_color="black",
        color="black",
    )
    password_input = ft.TextField(
        hint_text="Contraseña",
        password=True,
        can_reveal_password=True,
        border_radius=30,
        filled=True,
        bgcolor="#f5e6d3",
        border_color="transparent",
        cursor_color="black",
        color="black",
    )

    return ft.Container(
        width=350,
        height=450,
        bgcolor="#c1273d",
        border_radius=20,
        padding=30,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("👑", size=40),
                ft.Text("REY", size=40, weight="bold", color="white"),
                ft.Text(
                    "SOFTWARE DE INVENTARIOS", size=12, weight="bold", color="white"
                ),
                ft.Container(height=10),
                usuario_input,
                password_input,
                ft.Container(height=10),
                ft.ElevatedButton(
                    "INGRESAR",
                    width=250,
                    height=50,
                    bgcolor="#f2c500",
                    color="black",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=30)),
                    on_click=lambda _: on_login(
                        usuario_input.value, password_input.value
                    ),
                ),
                ft.Container(height=5),
                ft.Text("v2.0 © 2026 REY Inventarios", size=10, color="#ffb3b3"),
            ],
        ),
    )
