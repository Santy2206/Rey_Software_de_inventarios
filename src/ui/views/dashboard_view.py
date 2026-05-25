import flet as ft
from src.ui.components.sidebar import Sidebar
from src.ui.views.productos_view import ProductosView
from src.ui.views.ventas_view import VentasView
from src.ui.views.bodegas_view import BodegasView
from src.ui.views.movimientos_view import MovimientosView
from src.ui.views.clientes_view import ClientesView
from src.ui.views.reportes_view import ReportesView
from src.ui.views.bitacora_view import BitacoraView
from src.ui.components.cards import dashboard_card


def _DashboardHomeView():
    return ft.Column(
        expand=True,
        spacing=20,
        controls=[
            ft.Column(
                spacing=4,
                controls=[
                    ft.Text(
                        "Dashboard",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color="#222",
                    ),
                    ft.Text(
                        "Panel principal",
                        size=12,
                        color="grey",
                    ),
                ],
            ),
            ft.Row(
                spacing=20,
                controls=[
                    dashboard_card("PRODUCTOS", "0", "Total inventario"),
                    dashboard_card("VENTAS", "$0", "Ventas hoy"),
                    dashboard_card("BODEGAS", "0", "Bodegas activas"),
                    dashboard_card("CLIENTES", "0", "Clientes registrados"),
                ],
            ),
        ],
    )


VIEWS = {
    "dashboard": _DashboardHomeView,
    "PRODUCTOS": ProductosView,
    "VENTAS": VentasView,
    "BODEGAS": BodegasView,
    "MOVIMIENTOS": MovimientosView,
    "CLIENTES": ClientesView,
    "REPORTES": ReportesView,
    "BITACORA": BitacoraView,
}


def DashboardView(rol: str, on_logout):

    initial = _DashboardHomeView()
    content_area = ft.Column(
        expand=True,
        spacing=20,
        controls=initial.controls if isinstance(initial, ft.Column) else [initial],
    )

    def load_content(page_name: str):
        view = VIEWS[page_name]()
        content_area.controls.clear()
        if isinstance(view, ft.Column):
            content_area.controls.extend(view.controls)
        else:
            content_area.controls.append(view)
        content_area.update()

    return ft.Row(
        expand=True,
        spacing=0,
        controls=[
            Sidebar(on_navigate=load_content, on_logout=on_logout),
            ft.Container(
                expand=True,
                padding=20,
                bgcolor="#F5F5F5",
                content=content_area,
            ),
        ],
    )
