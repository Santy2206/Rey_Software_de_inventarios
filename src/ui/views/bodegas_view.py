import flet as ft


def BodegasView():
    return ft.Column(
        controls=[
            ft.Text("BODEGAS", size=30, weight="bold"),
            ft.Text("Aquí irán las bodegas", color="gray"),
        ]
    )
