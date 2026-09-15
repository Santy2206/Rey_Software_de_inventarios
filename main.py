"""
Punto de entrada de REY Inventarios.

Modos:
    python main.py            -> ventana de escritorio
    python main.py --web      -> navegador en http://localhost:8550
    REY_APP_MODE=web|desktop  -> alternativa por variable de entorno

Responsabilidades:
- Inicializa la aplicación Flet.
- Pasa el control a src/ui/app.py (función App).
- NO contiene lógica de negocio ni código de interfaz.
"""

import os
import sys

import flet as ft
from src.ui.app import App

DEFAULT_PORT = 8550


def _resolve_mode() -> str:
    env_mode = (os.environ.get("REY_APP_MODE") or "").strip().lower()
    if env_mode in {"web", "desktop"}:
        return env_mode
    if any(arg in {"--web", "web"} for arg in sys.argv[1:]):
        return "web"
    if any(arg in {"--desktop", "desktop"} for arg in sys.argv[1:]):
        return "desktop"
    return "desktop"


def main():
    mode = _resolve_mode()
    if mode == "web":
        # Servidor web en puerto fijo. Flet abrirá el navegador automáticamente.
        ft.app(
            target=App,
            view=ft.AppView.WEB_BROWSER,
            host="127.0.0.1",
            port=DEFAULT_PORT,
        )
    else:
        ft.app(target=App, view=ft.AppView.FLET_APP)


if __name__ == "__main__":
    main()
