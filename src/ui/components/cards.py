import flet as ft


def dashboard_card(titulo: str, numero: str, subtitulo: str) -> ft.Container:
    return ft.Container(
        width=300,
        height=130,
        bgcolor="white",
        border_radius=15,
        padding=20,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Text(titulo, size=14, weight="bold", color="#666666"),
                ft.Text(numero, size=15, weight="bold", color="#111111"),
                ft.Text(subtitulo, size=12, color="#999999"),
            ],
        ),
    )
