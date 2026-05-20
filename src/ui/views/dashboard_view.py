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
from src.ui.components.cards import dashboard_card


def sidebar_item(icon, text):
    return ft.Container(
        padding=10,
        border_radius=10,
        content=ft.Row(
            controls=[
                ft.Icon(icon, color="white", size=20),
                ft.Text(text, color="white", size=14),
            ]
        ),
    )


def DashboardView(rol: str, on_logout):

    sidebar = ft.Container(
        width=220,
        bgcolor="#b3001b",
        padding=20,
        content=ft.Column(
            expand=True,
            spacing=20,
            controls=[

                # LOGO / TITULO
                ft.Column(
                    spacing=5,
                    controls=[
                        ft.Text(
                            "👑 REY",
                            size=24,
                            weight="bold",
                            color="white",
                        ),
                        ft.Text(
                            "Inventarios",
                            color="white70",
                            size=12,
                        ),
                    ],
                ),

                ft.Divider(color="white24"),

                # MENÚ
                sidebar_item(ft.Icons.DASHBOARD, "Dashboard"),
                sidebar_item(ft.Icons.WAREHOUSE, "Bodegas"),
                sidebar_item(ft.Icons.INVENTORY_2, "Productos"),
                sidebar_item(ft.Icons.SWAP_HORIZ, "Movimientos"),
                sidebar_item(ft.Icons.SHOPPING_CART, "Ventas"),
                sidebar_item(ft.Icons.PEOPLE, "Clientes"),
                sidebar_item(ft.Icons.BAR_CHART, "Reportes"),
                sidebar_item(ft.Icons.DESCRIPTION, "Bitácora"),

                ft.Container(expand=True),

                # BOTON ABAJO
                ft.ElevatedButton(
                    "Cerrar sesión",
                    icon=ft.Icons.LOGOUT,
                    width=180,
                    bgcolor="#8b0015",
                    color="white",
                    on_click=lambda _: on_logout(),
                ),
            ],
        ),
    )

    # CONTENIDO DERECHO
    content = ft.Container(
        expand=True,
        padding=20,
        bgcolor="#f5f5f5",
        content=ft.Column(
            controls=[
                ft.Text(
                    "Dashboard",
                    size=30,
                    weight="bold",
                ),
                ft.Text(
                    "Panel Principal",
                    color="gray",
                ),
            ]
        ),
    )

    return ft.Row(
        expand=True,
        spacing=0,
        controls=[
            sidebar,
            content,
        ],
    )
        #AQUI