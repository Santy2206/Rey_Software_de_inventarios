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

import os
import threading
from pathlib import Path

import flet as ft
from src.core.local_db import run_query
from src.services.auth_service import AuthService
from src.sync.sync_service import SyncService
from src.ui.views.login_view import LoginView
from src.ui.views.dashboard_view import DashboardView


def App(page: ft.Page):
    page.title = "REY Software de Inventarios"
    page.padding = 0

    # El diseño de la app usa fondos claros hardcodeados (tarjetas blancas,
    # etc.) pero varios textos no fijan color explícito. Sin esto, Flet usa
    # el tema del sistema operativo (page.theme_mode por defecto es SYSTEM):
    # en Windows con modo oscuro, ese texto se renderiza en gris claro,
    # prácticamente ilegible sobre los fondos blancos.
    page.theme_mode = ft.ThemeMode.LIGHT

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
    _assets_dir = Path(
        os.environ.get(
            "FLET_ASSETS_DIR",
            str(Path(__file__).resolve().parents[2] / "assets"),
        )
    )
    page.window.icon = (_assets_dir / "icon.ico").as_posix()

    def navigate_to(view_name: str, **kwargs):
        page.clean()
        if view_name == "login":
            # Layout centrado solo para la pantalla de login
            page.bgcolor="#000000"
            page.vertical_alignment = ft.MainAxisAlignment.CENTER
            page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            page.add(LoginView(on_login=handle_login))
        elif view_name == "dashboard":
            # Resetear alineación: si queda centrada, el shell se ve vacío/roto
            page.bgcolor="#F5F5F5"
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

    def mostrar_pantalla_carga(mensaje: str):
        page.clean()
        page.bgcolor = "#000000"
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.add(
            ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.ProgressRing(color="#FFC200"),
                    ft.Container(height=15),
                    ft.Text(mensaje, color="white", size=14),
                ],
            )
        )
        page.update()

    def _hay_usuarios_locales() -> bool:
        try:
            fila = run_query("SELECT 1 FROM usuarios LIMIT 1", fetch_one=True)
            return bool(fila)
        except Exception:
            # Si ni siquiera se puede consultar, dejar que el flujo normal
            # (login) muestre el error real en vez de bloquear el arranque.
            return True

    def _ir_a_sesion():
        session = AuthService.restore_session()
        if session:
            navigate_to("dashboard", rol=session["rol"], user_id=session["id"])
        else:
            navigate_to("login")

    async def _terminar_arranque(resultado: dict):
        if not resultado.get("success") or not _hay_usuarios_locales():
            page.snack_bar = ft.SnackBar(
                content=ft.Text(
                    "No se pudo descargar la configuración inicial desde la "
                    "nube. Verifica tu conexión a internet e intenta de nuevo."
                ),
                bgcolor="#FFC200",
                show_close_icon=True,
            )
            page.snack_bar.open = True
        _ir_a_sesion()

    def _arrancar():
        """
        Primer arranque en un dispositivo nuevo: si la base local no tiene
        usuarios todavía, este equipo nunca se configuró. En vez de operar
        con una base vacía, se descargan los datos reales (usuarios,
        bodegas, clientes, productos, ...) ya existentes en el proyecto
        Supabase compartido, para que este dispositivo arranque con la
        misma información que los demás en vez de datos de ejemplo locales
        que chocarían al sincronizar.
        """
        if _hay_usuarios_locales():
            _ir_a_sesion()
            return

        mostrar_pantalla_carga("Configurando por primera vez...")

        def _worker():
            resultado = SyncService.descargar_inicial()
            page.run_task(_terminar_arranque, resultado)

        threading.Thread(target=_worker, daemon=True).start()

    _arrancar()
