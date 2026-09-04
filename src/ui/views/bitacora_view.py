"""
Vista de Bitácora.

Muestra el historial de acciones del sistema, cargado en vivo desde
BitacoraService (tabla 'bitacora'), con búsqueda por usuario, filtro
por tipo de acción y rango de fecha.

Sigue el mismo patrón que bodegas_view.py / productos_view.py:
  - Función pública BitacoraView() que envuelve la clase privada.
  - Clase _BitacoraView hereda de ft.Container.
  - La carga de datos corre en un hilo de fondo (threading), disparada
    desde did_mount().
  - Un solo page.update() al final de cada operación de carga.
  - SnackBar se registra en page.overlay desde did_mount().

Reglas:
    - SIN lógica de negocio — solo diseño e interacción de interfaz.
    - SIN llamadas directas a local_db, psycopg2 ni Supabase.
    - SIN ft.app() — esta vista es montada por dashboard_view.py.
"""

import threading
from datetime import datetime

import flet as ft

from src.services.bitacora_service import BitacoraService
from src.ui.components.status_header import StatusHeader
from src.ui.components.page_header import PageHeader

_COLORES_ACCION = {
    "LOGIN": ("#DBEAFE", "#1D4ED8"),
    "LOGIN_FALLIDO": ("#FEE2E2", "#B91C1C"),
    "ENTRADA": ("#DCFCE7", "#15803D"),
    "SALIDA": ("#FEE2E2", "#B91C1C"),
    "BAJA": ("#FEF3C7", "#B45309"),
    "MOVIMIENTO": ("#DBEAFE", "#1D4ED8"),
    "PRODUCTO": ("#EDE9FE", "#6D28D9"),
    "BODEGA": ("#FCE7F3", "#BE185D"),
    "CLIENTE": ("#FCE7F3", "#BE185D"),
    "VENTA": ("#DCFCE7", "#15803D"),
}


def BitacoraView():
    return ft.Column(controls=[_BitacoraView()])


class _BitacoraView(ft.Container):

    def __init__(self):
        super().__init__()

        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        self._registros: list[dict] = []

        # ── Barra de estado
        self._status_header = StatusHeader()

        # ── SnackBar
        self._snackbar = ft.SnackBar(content=ft.Text(""), show_close_icon=True)

        # ── Filtros
        self._buscar = ft.TextField(
            expand=True,
            hint_text="Buscar por usuario...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._aplicar_filtros,
        )

        self._filtro = ft.Dropdown(
            width=180,
            label="Acción",
            value="Todas",
            options=[
                ft.DropdownOption(key="Todas", text="Todas"),
                ft.DropdownOption(key="LOGIN", text="LOGIN"),
                ft.DropdownOption(key="LOGIN_FALLIDO", text="LOGIN_FALLIDO"),
                ft.DropdownOption(key="BODEGA", text="BODEGA"),
                ft.DropdownOption(key="PRODUCTO", text="PRODUCTO"),
                ft.DropdownOption(key="CLIENTE", text="CLIENTE"),
                ft.DropdownOption(key="MOVIMIENTO", text="MOVIMIENTO"),
                ft.DropdownOption(key="VENTA", text="VENTA"),
            ],
            on_select=self._aplicar_filtros,
        )

        self._fecha_inicio = ft.TextField(
            width=140,
            label="Desde",
            hint_text="DD/MM/AAAA",
            on_change=self._aplicar_filtros,
        )

        self._fecha_fin = ft.TextField(
            width=140,
            label="Hasta",
            hint_text="DD/MM/AAAA",
            on_change=self._aplicar_filtros,
        )

        # ── Tabla
        self._total = ft.Text(
            "0 registros",
            color="#4338CA",
            weight=ft.FontWeight.BOLD,
        )

        self._tabla = ft.DataTable(
            expand=True,
            border=ft.border.all(1, "#eeeeee"),
            border_radius=10,
            vertical_lines=ft.BorderSide(1, "#eeeeee"),
            horizontal_lines=ft.BorderSide(1, "#eeeeee"),
            heading_row_color="#fafafa",
            columns=[
                ft.DataColumn(ft.Text("Fecha / Hora")),
                ft.DataColumn(ft.Text("Usuario")),
                ft.DataColumn(ft.Text("Rol")),
                ft.DataColumn(ft.Text("Acción")),
                ft.DataColumn(ft.Text("Detalle")),
            ],
            rows=[],
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                self.header_section(),
                ft.Container(height=20),
                self.tabla_section(),
            ],
        )

    # ── Lifecycle ───────────────────────────────────────────────────────
    def did_mount(self):
        self.page.overlay.append(self._snackbar)
        self.page.update()
        self._status_header.load(self.page)
        threading.Thread(target=self._cargar_bitacora, daemon=True).start()

    def _cargar_bitacora(
        self,
        accion: str | None = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ):
        resultado = BitacoraService.get_all(
            accion=accion,
            fecha_inicio=self._parse_fecha(fecha_inicio),
            fecha_fin=self._parse_fecha(fecha_fin),
        )

        if resultado.get("success"):
            self._registros = resultado.get("data", [])
        else:
            self._registros = []
            if "Error" in resultado.get("message", ""):
                self._mostrar_snack(resultado["message"], error=True)

        self._refrescar_tabla()
        self.page.update()

    # ======================================================
    # HEADER
    # ======================================================

    def header_section(self):
        return PageHeader(
            title="Bitácora",
            subtitle="Registro de actividades del sistema",
            status_control=self._status_header.control,
        )

    # ======================================================
    # TABLA
    # ======================================================

    def tabla_section(self):
        return ft.Container(
            expand=True,
            bgcolor="white",
            border_radius=15,
            padding=20,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color=ft.Colors.BLACK12,
            ),
            content=ft.Column(
                expand=True,
                spacing=20,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(
                                        "Bitácora del Sistema",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        "Registro de acciones realizadas",
                                        size=11,
                                        color="grey",
                                    ),
                                ],
                            ),
                            ft.Container(
                                bgcolor="#EEF2FF",
                                border_radius=20,
                                padding=10,
                                content=ft.Row(
                                    spacing=5,
                                    controls=[
                                        ft.Icon(
                                            ft.Icons.LIST_ALT,
                                            color="#4338CA",
                                            size=16,
                                        ),
                                        self._total,
                                    ],
                                ),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            self._buscar,
                            self._filtro,
                            self._fecha_inicio,
                            self._fecha_fin,
                        ],
                    ),
                    ft.Divider(),
                    self._tabla,
                ],
            ),
        )

    # ======================================================
    # DATOS -> FILAS
    # ======================================================

    def _refrescar_tabla(self):
        texto = (self._buscar.value or "").lower()

        self._tabla.rows = [
            self._crear_fila(r)
            for r in self._registros
            if texto in (r.get("usuario") or "").lower()
        ]
        self._total.value = f"{len(self._tabla.rows)} registros"

    def _crear_fila(self, registro: dict):
        fecha = registro.get("fecha")
        if isinstance(fecha, str):
            fecha_str = fecha
        elif hasattr(fecha, "strftime"):
            fecha_str = fecha.strftime("%d/%m/%Y %H:%M")
        else:
            fecha_str = str(fecha or "—")

        usuario = registro.get("usuario") or "—"
        rol = (registro.get("rol") or "—").capitalize()
        accion = registro.get("accion") or "—"

        detalles = registro.get("detalles") or {}
        descripcion = (
            detalles.get("descripcion", "")
            if isinstance(detalles, dict)
            else str(detalles)
        )

        fondo, texto = _COLORES_ACCION.get(accion, ("#F3F4F6", "#374151"))

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(fecha_str)),
                ft.DataCell(ft.Text(usuario)),
                ft.DataCell(ft.Text(rol)),
                ft.DataCell(
                    ft.Container(
                        bgcolor=fondo,
                        border_radius=20,
                        padding=6,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            accion,
                            color=texto,
                            weight=ft.FontWeight.BOLD,
                            size=11,
                        ),
                    )
                ),
                ft.DataCell(ft.Text(descripcion)),
            ]
        )

    # ======================================================
    # FILTROS (búsqueda + acción + rango de fecha)
    # ======================================================

    def _aplicar_filtros(self, e=None):
        accion = self._filtro.value
        accion = accion if accion and accion != "Todas" else None

        self._cargar_bitacora(
            accion=accion,
            fecha_inicio=self._fecha_inicio.value,
            fecha_fin=self._fecha_fin.value,
        )

    def _parse_fecha(self, s: str):
        if not s:
            return None
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except ValueError:
            return None

    # ======================================================
    # FEEDBACK
    # ======================================================

    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        self.page.update()
