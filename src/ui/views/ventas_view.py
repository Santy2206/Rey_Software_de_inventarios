import flet as ft


def VentasView():
    return ft.Column(
        controls=[
            ft.Text("VENTAS", size=30, weight="bold"),
            ft.Text("Aqui van las ventas", color="gray"),
        ]
    )
