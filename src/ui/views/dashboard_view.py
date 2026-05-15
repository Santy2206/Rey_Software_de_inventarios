import flet as ft


def DashboardView(rol: str, on_logout):
    return (
        ft.Container(
            expand=True,
            bgcolor="#f5f5f5",
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Dashboard", size=30, weight="bold"),
                            ft.Text("Panel Principal", color="gray"),
                        ],
                    ),
                    ft.Container(
                        bgcolor="white",
                        padding=10,
                        border_radius=30,
                        content=ft.Text("🟢 Online", color="green"),
                    ),
                ]
            ),
        ),
    )
