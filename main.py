"""
Punto de entrada de REY Inventarios.

Responsabilidades:
- Inicializa la aplicación Flet.
- Pasa el control a src/ui/app.py (función App).
- NO contiene lógica de negocio ni código de interfaz.

Uso:
    python main.py
"""

import flet as ft
from src.ui.app import App

ft.app(target=App, view=ft.AppView.WEB_BROWSER)
