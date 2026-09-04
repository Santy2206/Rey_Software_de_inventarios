import flet as ft
from src.ui.components.sidebar import Sidebar
from src.ui.components.status_header import StatusHeader
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
from src.services.ventas_service import VentasService
from src.services.clientes_service import ClientesService


def _metric_count(result: dict) -> str:
    """Convierte la respuesta de un service en un número para la tarjeta."""
    if result.get("success") and result.get("data"):
        return str(len(result["data"]))
    return "0"


class _DashboardHomeView(ft.Column):
    def __init__(self):
        super().__init__(spacing=20, tight=True)
        self._status_header = StatusHeader()
        self._cards_row = ft.Row(
            spacing=20,
            wrap=True,
            run_spacing=20,
            controls=[],
        )

        self.controls = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
                    self._status_header.control,
                ],
            ),
            self._cards_row,
        ]

    def did_mount(self):
        self._status_header.load(self.page)
        self._cargar_metricas()

    def _cargar_metricas(self):
        try:
            productos = _metric_count(ProductosService.get_all())
        except Exception:
            productos = "0"

        try:
            bodegas = _metric_count(BodegasService.get_all())
        except Exception:
            bodegas = "0"

        try:
            res_ventas = VentasService.total_hoy()
            ventas = (
                f"${float(res_ventas['data']):,.0f}"
                if res_ventas.get("success")
                else "$0"
            )
        except Exception:
            ventas = "$0"

        try:
            clientes = _metric_count(ClientesService.get_all())
        except Exception:
            clientes = "0"

        self._cards_row.controls = [
            dashboard_card("PRODUCTOS", productos, "Total inventario"),
            dashboard_card("VENTAS", ventas, "Ventas hoy"),
            dashboard_card("BODEGAS", bodegas, "Bodegas activas"),
            dashboard_card("CLIENTES", clientes, "Clientes registrados"),
        ]
        self.page.update()


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


def DashboardView(rol: str, user_id: str | None, on_logout):
    """
    Vista principal del dashboard.

    Parámetros:
        rol:      rol del usuario autenticado (ej: "admin", "vendedor").
        user_id:  id de la fila en la tabla 'usuarios' (UUID local).
                  Se propaga a las vistas hijas que lo necesiten para
                  registrar movimientos, ventas o bitácora. Las vistas
                  actuales (movimientos_view, ventas_view) obtienen este
                  mismo id a través de AuthService.get_usuario_id().
        on_logout: callback para cerrar sesión.
    """

    _dashboard_state = {"user_id": user_id, "rol": rol}

    content_area = ft.Column(
        expand=True,
        spacing=20,
        scroll=ft.ScrollMode.AUTO,
        controls=[_DashboardHomeView()],
    )

    # Se define primero para pasarla al Sidebar; sidebar se asigna después.
    def load_content(page_name: str):
        sidebar.set_active(page_name)
        content_area.controls.clear()
        content_area.controls.append(VIEWS[page_name]())
        content_area.update()

    sidebar = Sidebar(on_navigate=load_content, on_logout=on_logout)
    sidebar.set_active("dashboard")

    return ft.Row(
        expand=True,
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            sidebar,
            ft.Container(
                expand=True,
                padding=20,
                bgcolor="#F5F5F5",
                content=content_area,
            ),
        ],
    )
