import flet as ft


def ClientesView():
    return ft.Column(
        controls=[
            ft.Text("CLIENTES", size=30, weight="bold"),
            ft.Text("Aquí irán los clientes", color="gray"),
        ]
    )
