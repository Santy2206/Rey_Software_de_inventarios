import flet as ft
from ui.views.login import LoginView
from services.auth_service import AuthService


def main(page: ft.Page):
    page.title = "REY Inventarios"
    page.bgcolor = "#b3001b"
    page.vertical_alignment = "center"

    # Esta función une el Servicio con la Vista
    def manejar_login(user, pwd):
        resultado = AuthService.login(user, pwd)

        if resultado["success"]:
            page.snack_bar = ft.SnackBar(ft.Text(resultado["message"]), bgcolor="green")

        else:
            page.snack_bar = ft.SnackBar(ft.Text(resultado["message"]), bgcolor="black")

        page.snack_bar.open = True
        page.update()

    # Cargamos la vista pasándole el manejador
    page.add(
        ft.Row(alignment="center", controls=[LoginView(on_login_click=manejar_login)])
    )


ft.app(target=main, view=ft.AppView.WEB_BROWSER)
