import flet as ft


def BitacoraView():
    return ft.Column(
        controls=[
            ft.Text("BITACORA", size=30, weight="bold"),
            ft.Text("Aquí irán lo bitacora", color="gray"),
        ]
    )
