"""
Vista de la pantalla principal del dashboard.

Muestra tarjetas de resumen y opciones de navegación
después de un inicio de sesión exitoso.
El diseño se adapta según el rol del usuario (administrador / vendedor).

Parámetros:
    rol       (str)      : Rol del usuario, usado para mostrar u ocultar
                        funciones de administrador.
    on_logout (callable) : Se llama (sin argumentos) cuando el usuario
                        hace clic en 'Cerrar Sesión'.

Retorna:
    ft.Container: El layout completo del dashboard, listo para agregar a la página.

Reglas:
    - SIN lógica de negocio — solo diseño e interfaz condicional.
    - Los widgets de tarjetas se importan desde src/ui/components/cards.py.
    - SIN acceso al objeto `page` — se comunica solo mediante callbacks.
"""

import flet as ft
from src.ui.components.cards import dashboard_card  # ← import the card component


def DashboardView(rol: str, on_logout):  # ✅ correct signature

    return ft.Container(  # ✅ single return, the real dashboard
        expand=True,
        bgcolor="#f5f5f5",
        padding=20,
        content=ft.Column(
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Dashboard", size=30, weight="bold"),
                        ft.Text(
                            "Panel Principal", color="gray"
                        ),  # ✅ lowercase 'color'
                    ],
                ),
                ft.Container(
                    bgcolor="white",
                    padding=10,
                    border_radius=30,
                    content=ft.Text("🟢 Online", color="green"),
                ),
                # Example cards — replace with real data later
                ft.Row(
                    controls=[
                        dashboard_card("Productos", "0", "Total en inventario"),
                        dashboard_card("Ventas hoy", "$0", "Últimas 24 h"),
                    ]
                ),
                ft.ElevatedButton(
                    "Cerrar Sesión",
                    on_click=lambda _: on_logout(),  # ✅ wires the logout callback
                    bgcolor="#c1273d",
                    color="white",
                ),
            ]
        ),
    )
