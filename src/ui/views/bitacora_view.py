"""
Vista de Bitácora.

Muestra el historial de acciones del sistema, cargado en vivo desde
BitacoraService (tabla 'bitacora'), con búsqueda por usuario y filtro
por tipo de acción.

Sigue el mismo patrón que bodegas_view.py / productos_view.py:
  - Función pública BitacoraView() que envuelve la clase privada.
  - Clase _BitacoraView hereda de ft.Container.
  - La carga de datos corre en un hilo de fondo (threading), disparada
    desde did_mount().
"""

import threading
import flet as ft

from src.services.bitacora_service import BitacoraService

_COLORES_ACCION = {
    "LOGIN": ("#DBEAFE", "#1D4ED8"),
    "ENTRADA": ("#DCFCE7", "#15803D"),
    "SALIDA": ("#FEE2E2", "#B91C1C"),
    "BAJA": ("#FEF3C7", "#B45309"),
    "MOVIMIENTO": ("#DBEAFE", "#1D4ED8"),
    "PRODUCTO": ("#EDE9FE", "#6D28D9"),
    "BODEGA": ("#FCE7F3", "#BE185D"),
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
        threading.Thread(target=self._cargar_bitacora, daemon=True).start()

    def _cargar_bitacora(self):
        resultado = BitacoraService.get_all()
        self._registros = resultado["data"] if resultado["success"] else []
        self._refrescar_tabla()
        self.page.update()

    # ======================================================
    # HEADER
    # ======================================================

    def header_section(self):

        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            "Bitácora",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="#222",
                        ),
                        ft.Text(
                            "Registro de actividades del sistema",
                            size=12,
                            color="grey",
                        ),
                    ],
                ),
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.Container(
                            bgcolor="#E8FFF0",
                            border_radius=20,
                            padding=ft.padding.symmetric(
                                horizontal=12,
                                vertical=8,
                            ),
                            content=ft.Row(
                                spacing=5,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.CHECK_CIRCLE,
                                        color="green",
                                        size=16,
                                    ),
                                    ft.Text(
                                        "Online (Sincronizado)",
                                        color="green",
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            bgcolor="white",
                            border_radius=15,
                            padding=10,
                            shadow=ft.BoxShadow(
                                spread_radius=1,
                                blur_radius=8,
                                color=ft.Colors.BLACK12,
                            ),
                            content=ft.Row(
                                spacing=10,
                                controls=[
                                    ft.CircleAvatar(
                                        bgcolor="#b3001b",
                                        content=ft.Text(
                                            "A",
                                            color="white",
                                        ),
                                    ),
                                    ft.Column(
                                        spacing=0,
                                        controls=[
                                            ft.Text(
                                                "admin",
                                                weight=ft.FontWeight.BOLD,
                                            ),
                                            ft.Text(
                                                "Administrador",
                                                size=11,
                                                color="grey",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ],
        )

    # ======================================================
    # TABLA
    # ======================================================

    def tabla_section(self):

        self.buscar = ft.TextField(
            expand=True,
            hint_text="Buscar por usuario...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._aplicar_filtros,
        )

        self.filtro = ft.Dropdown(
            on_change=self._aplicar_filtros,
            width=180,
            label="Acción",
            value="Todas",
            options=[
                ft.DropdownOption("Todas"),
                ft.DropdownOption("LOGIN"),
                ft.DropdownOption("ENTRADA"),
                ft.DropdownOption("SALIDA"),
                ft.DropdownOption("BAJA"),
                ft.DropdownOption("MOVIMIENTO"),
                ft.DropdownOption("PRODUCTO"),
                ft.DropdownOption("BODEGA"),
            ],
        )

        self.total = ft.Text(
            "0 registros",
            color="#4338CA",
            weight=ft.FontWeight.BOLD,
        )

        self.tabla = ft.DataTable(
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
                                        self.total,
                                    ],
                                ),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            self.buscar,
                            self.filtro,
                        ],
                    ),
                    ft.Divider(),
                    self.tabla,
                ],
            ),
        )

    # ======================================================
    # DATOS -> FILAS
    # ======================================================

    def _refrescar_tabla(self):
        self.tabla.rows = [self._crear_fila(r) for r in self._registros]
        self.total.value = f"{len(self.tabla.rows)} registros"

    def _crear_fila(self, registro: dict):

        fecha = registro.get("fecha")
        fecha_str = (
            fecha.strftime("%d/%m/%Y %H:%M")
            if hasattr(fecha, "strftime")
            else str(fecha or "—")
        )

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
            ],
        )

    # ======================================================
    # FILTROS (búsqueda + acción, combinados)
    # ======================================================

    def _aplicar_filtros(self, e=None):

        texto = (self.buscar.value or "").lower()
        accion_sel = self.filtro.value

        for fila in self.tabla.rows:
            usuario = fila.cells[1].content.value.lower()
            accion_fila = fila.cells[3].content.content.value

            visible = texto in usuario
            if accion_sel and accion_sel != "Todas":
                visible = visible and accion_fila == accion_sel

            fila.visible = visible

        self.update()
