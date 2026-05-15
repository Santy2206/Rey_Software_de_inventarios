import flet as ft
from views.login import LoginView
from services.auth_service import AuthService


def main(page: ft.Page):
    page.title = "REY Inventarios"
    page.bgcolor = "#b3001b"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"

    def manejar_login(user, pwd):
        # We call the service and wait for the dictionary result
        resultado = AuthService.login(user, pwd)

        if resultado["success"]:
            # Action: Success!
            page.controls.clear()
            page.add(
                ft.Column(
                    [
                        ft.Text(
                            f"ACCESO CONCEDIDO: {resultado['rol'].upper()}",
                            size=30,
                            color="white",
                            weight="bold",
                        ),
                        ft.ElevatedButton(
                            "Cerrar Sesión", on_click=lambda _: main(page)
                        ),
                    ],
                    horizontal_alignment="center",
                )
            )
        else:
            # Action: Failure - Show the message in a SnackBar
            page.snack_bar = ft.SnackBar(
                content=ft.Text(resultado["message"]),
                bgcolor="black",
                show_close_icon=True,
            )
            page.snack_bar.open = True

        # CRITICAL: This is what makes the "Something" happen visually
        page.update()

    # Initial screen setup
    page.clean()
    page.add(LoginView(on_login_click=manejar_login))
    page.update()


ft.app(target=main, view=ft.AppView.WEB_BROWSER)
