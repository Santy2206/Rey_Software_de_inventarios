import flet as ft


def ProductosView():
    return ft.Column(
        controls=[
            ft.Text("PRODUCTOS", size=30, weight="bold"),
            ft.Text("Aquí irán los productos", color="gray"),
        ]
    )
