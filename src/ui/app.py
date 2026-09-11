"""
Router principal y manejador de estado de la página.

Es dueño del objeto `page` de Flet y es responsable de:
- Navegar entre vistas (login → dashboard → ...).
- Pasar callbacks (on_login, on_logout) a las vistas.
- Manejar las acciones principales del usuario.
- Mostrar SnackBars con mensajes de error.

La navegación se hace a través de la función interna `navigate_to(nombre_vista)`.

Reglas:
    - Es el ÚNICO archivo que llama page.clean(), page.add() y page.update().
    - Las vistas NUNCA deben recibir el objeto `page` directamente.
"""

import threading

import flet as ft
from src.services.auth_service import AuthService
from src.ui.views.login_view import LoginView
from src.ui.views.dashboard_view import DashboardView


def App(page: ft.Page):
    page.title = "REY Inventarios"
    page.padding = 0

    # Hacer que page.update() sea seguro desde hilos de fondo:
    # si se llama desde un thread secundario, se programa en el loop de UI.
    _orig_update = page.update

    def _safe_update(*controls):
        if threading.current_thread() is threading.main_thread():
            return _orig_update(*controls)
        try:
            loop = page.session.connection.loop
            loop.call_soon_threadsafe(lambda: _orig_update(*controls))
        except Exception:
            # Fallback por si no se puede acceder al loop
            _orig_update(*controls)

    page.update = _safe_update

    # Configuración de la ventana de escritorio
    page.window.width = 1280
    page.window.height = 720
    page.window.min_width = 1024
    page.window.min_height = 600
    page.window.maximized = False
    page.window.minimized = False
    page.window.visible = True
    page.window.focused = True
    page.window.icon = "assets/icon.ico"

    def navigate_to(view_name: str, **kwargs):
        page.clean()
        if view_name == "login":
            # Layout centrado solo para la pantalla de login
            page.bgcolor = "#b3001b"
            page.vertical_alignment = ft.MainAxisAlignment.CENTER
            page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            page.add(LoginView(on_login=handle_login))
        elif view_name == "dashboard":
            # Resetear alineación: si queda centrada, el shell se ve vacío/roto
            page.bgcolor = "#F5F5F5"
            page.vertical_alignment = ft.MainAxisAlignment.START
            page.horizontal_alignment = ft.CrossAxisAlignment.START
            page.add(
                DashboardView(
                    rol=kwargs.get("rol"),
                    user_id=kwargs.get("user_id"),
                    on_logout=handle_logout,
                )
            )
        page.update()

    def handle_login(username: str, password: str):
        result = AuthService.login(username, password)
        if result["success"]:
            navigate_to("dashboard", rol=result["rol"], user_id=result["id"])
        else:
            page.snack_bar = ft.SnackBar(
                content=ft.Text(result["message"]),
                bgcolor="black",
                show_close_icon=True,
            )
            page.snack_bar.open = True
            page.update()

    def handle_logout():
        AuthService.logout()
        navigate_to("login")

    # Restaurar sesión local al arrancar (evita re-login al cambiar de modo)
    session = AuthService.restore_session()
    if session:
        navigate_to("dashboard", rol=session["rol"], user_id=session["id"])
    else:
        navigate_to("login")
