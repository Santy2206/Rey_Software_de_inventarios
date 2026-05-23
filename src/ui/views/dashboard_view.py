import flet as ft
from src.ui.components.sidebar import Sidebar
from src.ui.views.productos_view import ProductosView
from src.ui.views.ventas_view import VentasView
from src.ui.views.bodegas_view import BodegasView
from src.ui.views.movimientos_view import MovimientosView
from src.ui.views.clientes_view import ClientesView
from src.ui.views.reportes_view import ReportesView
from src.ui.views.bitacora_view import BitacoraView

# ... rest of imports

VIEWS = {
    "dashboard": lambda: ft.Column(
        controls=[ft.Text("DASHBOARD", size=30, weight="bold")]
    ),
    "PRODUCTOS": ProductosView,
    "VENTAS": VentasView,
    "BODEGAS": BodegasView,
    "MOVIMIENTOS": MovimientosView,
    "CLIENTES": ClientesView,
    "REPORTES": ReportesView,
    "BITACORA": BitacoraView,
}


def DashboardView(rol: str, on_logout):
    content_area = ft.Column(
        expand=True, spacing=20, controls=VIEWS["dashboard"]().controls
    )

    def load_content(page_name):
        content_area.controls.clear()
        content_area.controls.extend(VIEWS[page_name]().controls)
        content_area.update()

    return ft.Row(
        expand=True,
        spacing=0,
        controls=[
            Sidebar(on_navigate=load_content, on_logout=on_logout),
            ft.Container(
                expand=True, padding=20, bgcolor="#F5F5F5", content=content_area
            ),
        ],
    )
