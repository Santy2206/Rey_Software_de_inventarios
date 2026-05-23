import flet as ft


def ReportesView():
    return ft.Column(
        controls=[
            ft.Text("REPORTES", size=30, weight="bold"),
            ft.Text("Aquí irán los reportes", color="gray"),
        ]
    )
