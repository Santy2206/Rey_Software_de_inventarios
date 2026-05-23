import flet as ft


def MovimientosView():
    return ft.Column(
        controls=[
            ft.Text("MOVIMIENTOS", size=30, weight="bold"),
            ft.Text("Aquí irán los movimientos", color="gray"),
        ]
    )
