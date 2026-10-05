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

# En el ejecutable instalado (REY_Inventarios.exe) se trabaja desde la carpeta
# del programa para que siempre encuentre su archivo .env.
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

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


def _resolve_assets_dir() -> str:
    """Devuelve la ruta absoluta de los assets (empaquetado o desarrollo)."""
    if getattr(sys, "frozen", False):
        return os.path.abspath(
            os.path.join(os.path.dirname(sys.executable), "_internal", "assets")
        )
    return os.path.abspath("assets")


def main():
    mode = _resolve_mode()
    assets_dir = _resolve_assets_dir()
    os.environ["FLET_ASSETS_DIR"] = assets_dir
    if mode == "web":
        # Servidor web en puerto fijo. Flet abrirá el navegador automáticamente.
        # Opcional: REY_HOST=0.0.0.0 permite abrir la app desde otros equipos de
        # la red y REY_HEADLESS=1 evita que se abra el navegador automáticamente.
        host = os.environ.get("REY_HOST", "127.0.0.1")
        port = int(os.environ.get("REY_PORT", DEFAULT_PORT))
        headless = os.environ.get("REY_HEADLESS", "").strip() in {"1", "true", "yes"}
        # Sirve los archivos de Flutter (CanvasKit) desde la propia app y no
        # desde el CDN de Google: la app funciona sin internet en la red local.
        no_cdn = os.environ.get("REY_NO_CDN", "1").strip() not in {"0", "false", "no"}
        ft.run(
            App,
            view=None if headless else ft.AppView.WEB_BROWSER,
            assets_dir=assets_dir,
            host=host,
            port=port,
            no_cdn=no_cdn,
        )
    else:
        ft.run(App, view=ft.AppView.FLET_APP, assets_dir=assets_dir)


if __name__ == "__main__":
    main()
