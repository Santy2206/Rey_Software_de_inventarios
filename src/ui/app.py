import flet as ft
from src.services.auth_service import AuthService
from src.ui.views.login_view import LoginView
from src.ui.views.dashboard_view import DashboardView


def App(page: ft.Page):
    page.title = "REY Inventarios"
    page.bgcolor = "#b3001b"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"

    def navigate_to(view_name: str, **kwargs):
        page.clean()
        if view_name == "login":
            page.add(LoginView(on_login=handle_login))
        elif view_name == "dashboard":
            page.add(DashboardView(rol=kwargs.get("rol"), on_logout=handle_logout))
        page.update()

    def handle_login(username: str, password: str):
        result = AuthService.login(username, password)
        if result["success"]:
            navigate_to("dashboard", rol=result["rol"])
        else:
            page.snack_bar = ft.SnackBar(
                content=ft.Text(result["message"]),
                bgcolor="black",
                show_close_icon=True,
            )
            page.snack_bar.open = True
            page.update()

    def handle_logout():
        navigate_to("login")

    navigate_to("login")  # Initial screen
