import flet as ft


def sidebar_item(icon, text, page_name, on_click):
    return ft.Container(
        padding=10,
        border_radius=10,
        on_click=lambda e: on_click(page_name),
        content=ft.Row(
            controls=[
                ft.Icon(icon, color="white", size=20),
                ft.Text(text, color="white", size=14),
            ]
        ),
    )


def Sidebar(on_navigate, on_logout):
    return ft.Container(
        width=220,
        bgcolor="#b3001b",
        padding=20,
        content=ft.Column(
            expand=True,
            spacing=20,
            controls=[
                ft.Text("👑 REY", size=24, weight="bold", color="white"),
                ft.Divider(color="white24"),
                sidebar_item(ft.Icons.DASHBOARD, "Dashboard", "dashboard", on_navigate),
                sidebar_item(ft.Icons.WAREHOUSE, "Bodegas", "BODEGAS", on_navigate),
                sidebar_item(
                    ft.Icons.INVENTORY_2, "Productos", "PRODUCTOS", on_navigate
                ),
                sidebar_item(
                    ft.Icons.SWAP_HORIZ, "Movimientos", "MOVIMIENTOS", on_navigate
                ),
                sidebar_item(ft.Icons.SHOPPING_CART, "Ventas", "VENTAS", on_navigate),
                sidebar_item(ft.Icons.PEOPLE, "Clientes", "CLIENTES", on_navigate),
                sidebar_item(ft.Icons.BAR_CHART, "Reportes", "REPORTES", on_navigate),
                sidebar_item(ft.Icons.DESCRIPTION, "Bitácora", "BITACORA", on_navigate),
                ft.Container(expand=True),
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
