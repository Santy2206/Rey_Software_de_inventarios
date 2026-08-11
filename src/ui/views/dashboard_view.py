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
from src.services.productos_service import ProductosService
from src.services.bodegas_service import BodegasService


def _metric_count(result: dict) -> str:
    """Convierte la respuesta de un service en un número para la tarjeta."""
    if result.get("success") and result.get("data"):
        return str(len(result["data"]))
    return "0"


def _DashboardHomeView():
    try:
        productos = _metric_count(ProductosService.get_all())
    except Exception:
        productos = "0"

    try:
        bodegas = _metric_count(BodegasService.get_all())
    except Exception:
        bodegas = "0"

    return ft.Column(
        spacing=20,
        tight=True,
        controls=[
            ft.Column(
                spacing=4,
                tight=True,
                controls=[
                    ft.Text(
                        "Dashboard",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color="#222222",
                    ),
                    ft.Text(
                        "Panel principal",
                        size=12,
                        color="#666666",
                    ),
                ],
            ),
            ft.Row(
                spacing=20,
                wrap=True,
                run_spacing=20,
                controls=[
                    dashboard_card("PRODUCTOS", productos, "Total inventario"),
                    dashboard_card("VENTAS", "$0", "Ventas hoy"),
                    dashboard_card("BODEGAS", bodegas, "Bodegas activas"),
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
    content_area = ft.Column(
        expand=True,
        spacing=20,
        scroll=ft.ScrollMode.AUTO,
        controls=[_DashboardHomeView()],
    )

    def load_content(page_name: str):
        content_area.controls.clear()
        content_area.controls.append(VIEWS[page_name]())
        content_area.update()

    return ft.Row(
        expand=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            Sidebar(on_navigate=load_content, on_logout=on_logout),
            ft.Container(
                expand=True,
                padding=20,
                bgcolor="#F5F5F5",
                alignment=ft.alignment.top_left,
                content=content_area,
            ),
        ],
    )
