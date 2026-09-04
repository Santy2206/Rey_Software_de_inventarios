"""
Vista de Reportes.

Permite seleccionar un tipo de reporte, aplicar filtros de fecha,
generar una vista previa en tabla y exportar a CSV o Excel.

Sigue el mismo patrón que bodegas_view.py:
  - Función pública ReportesView() que envuelve la clase privada.
  - Clase _ReportesView hereda de ft.Container.
  - La carga de datos corre en un hilo de fondo (threading).
  - SnackBar se registra en page.overlay desde did_mount().
  - Un solo page.update() al final de cada operación.

Reglas:
    - SIN lógica de negocio — solo diseño e interacción de interfaz.
    - SIN llamadas directas a parsers/generators — todo pasa por
      src.services.reportes_service.
    - SIN ft.app() — esta vista es montada por dashboard_view.py.
"""

import threading

import flet as ft

from src.services.reportes_service import ReportesService

_TIPOS_REPORTE = [
    ("Bodegas/Productos", ft.Icons.WAREHOUSE, "#1976D2"),
    ("Ventas", ft.Icons.SHOPPING_CART, "#388E3C"),
    ("Ventas Realizadas", ft.Icons.BAR_CHART, "#F57C00"),
    ("Productos por Bodega", ft.Icons.INVENTORY, "#7B1FA2"),
]

_MESES = [
    ("Todos", None),
    ("Enero", 1),
    ("Febrero", 2),
    ("Marzo", 3),
    ("Abril", 4),
    ("Mayo", 5),
    ("Junio", 6),
    ("Julio", 7),
    ("Agosto", 8),
    ("Septiembre", 9),
    ("Octubre", 10),
    ("Noviembre", 11),
    ("Diciembre", 12),
]


def ReportesView():
    return ft.Column(controls=[_ReportesView()])


class _ReportesView(ft.Container):
    def __init__(self):
        super().__init__()

        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        # ── Estado ─────────────────────────────────────────────────────────
        self._tipo_seleccionado: str | None = None
        self._filas: list[dict] = []
        self._botones_reporte: list = []

        # ── SnackBar ───────────────────────────────────────────────────────
        self._snackbar = ft.SnackBar(content=ft.Text(""), show_close_icon=True)

        # ── Filtros ────────────────────────────────────────────────────────
        self._dropdown_mes = ft.Dropdown(
            width=180,
            label="Mes",
            value=None,
            options=[
                ft.DropdownOption(key=str(key) if key is not None else "", text=nombre)
                for nombre, key in _MESES
            ],
        )

        anios = [str(a) for a in range(2024, 2031)]
        self._dropdown_anio = ft.Dropdown(
            width=120,
            label="Año",
            value="2026",
            options=[ft.DropdownOption(a) for a in anios],
        )

        # ── Tabla de resultados ────────────────────────────────────────────
        self._tabla = ft.DataTable(
            expand=True,
            border=ft.border.all(1, "#eeeeee"),
            border_radius=10,
            vertical_lines=ft.BorderSide(1, "#eeeeee"),
            horizontal_lines=ft.BorderSide(1, "#eeeeee"),
            heading_row_color="#fafafa",
            columns=[ft.DataColumn(ft.Text("Resultado"))],
            rows=[],
        )

        self.content = ft.Column(
            expand=True,
            controls=[
                self.header(),
                ft.Container(height=20),
                self.filters_section(),
                ft.Container(height=20),
                self.report_area(),
            ],
        )

    # ── Lifecycle ──────────────────────────────────────────────────────────
    def did_mount(self):
        self.page.overlay.append(self._snackbar)
        self.page.update()

    # ============================================================
    # HEADER
    # ============================================================
    def header(self):
        return ft.Column(
            spacing=5,
            controls=[
                ft.Text(
                    "Reportes",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color="#222",
                ),
                ft.Text(
                    "Genera y exporta reportes del sistema",
                    size=12,
                    color="grey",
                ),
            ],
        )

    # ============================================================
    # FILTROS
    # ============================================================
    def filters_section(self):
        botones = [
            self._report_button(titulo, icon, color)
            for titulo, icon, color in _TIPOS_REPORTE
        ]

        return ft.Container(
            bgcolor="white",
            border_radius=15,
            padding=20,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color=ft.Colors.BLACK12,
            ),
            content=ft.Column(
                spacing=20,
                controls=[
                    ft.Row(spacing=10, controls=botones),
                    ft.Row(
                        spacing=10,
                        controls=[
                            self._dropdown_mes,
                            self._dropdown_anio,
                            ft.ElevatedButton(
                                "Generar Reporte",
                                bgcolor="#d32f2f",
                                color="white",
                                height=45,
                                on_click=self._generar_reporte,
                            ),
                            ft.ElevatedButton(
                                "Exportar CSV",
                                icon=ft.Icons.DOWNLOAD,
                                bgcolor="#4caf50",
                                color="white",
                                height=45,
                                on_click=lambda e: self._exportar("csv"),
                            ),
                            ft.ElevatedButton(
                                "Exportar Excel",
                                icon=ft.Icons.FILE_DOWNLOAD,
                                bgcolor="#2196F3",
                                color="white",
                                height=45,
                                on_click=lambda e: self._exportar("xlsx"),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _report_button(self, titulo, icon, color):
        contenedor = ft.Container(
            padding=12,
            border_radius=10,
            bgcolor="#f8f8f8",
            border=ft.border.all(1, "#e0e0e0"),
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(icon, size=18, color=color),
                    ft.Text(titulo, size=12, color="#444"),
                ],
            ),
        )

        def _seleccionar(e):
            self._tipo_seleccionado = titulo
            contenedor.bgcolor = "#e3f2fd"
            contenedor.border = ft.border.all(2, color)
            for otro in self._botones_reporte:
                if otro is not contenedor:
                    otro.bgcolor = "#f8f8f8"
                    otro.border = ft.border.all(1, "#e0e0e0")
            self.update()

        contenedor.on_click = _seleccionar
        self._botones_reporte.append(contenedor)
        return contenedor

    # ============================================================
    # ÁREA DE REPORTE
    # ============================================================
    def report_area(self):
        self._contador_label = ft.Text(
            "0 registros",
            color="#4338CA",
            weight=ft.FontWeight.BOLD,
        )
        return ft.Container(
            expand=True,
            bgcolor="white",
            border_radius=15,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color=ft.Colors.BLACK12,
            ),
            padding=20,
            content=ft.Column(
                expand=True,
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Vista previa",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                            ),
                            self._contador_label,
                        ],
                    ),
                    ft.Divider(),
                    self._tabla,
                ],
            ),
        )

    # ============================================================
    # GENERAR / EXPORTAR
    # ============================================================
    def _generar_reporte(self, e=None):
        if not self._tipo_seleccionado:
            self._mostrar_snack("⚠️ Selecciona un tipo de reporte.", error=True)
            return

        def _worker():
            anio = int(self._dropdown_anio.value) if self._dropdown_anio.value else None
            mes_raw = self._dropdown_mes.value
            mes = int(mes_raw) if mes_raw and mes_raw.isdigit() else None

            resultado = ReportesService.generar(
                self._tipo_seleccionado, anio=anio, mes=mes
            )

            if not resultado.get("success"):
                self._filas = []
                self._mostrar_snack(resultado.get("message", ""), error=True)
            else:
                self._filas = resultado["data"].get("filas", [])
                self._mostrar_snack(
                    resultado.get("message", "Reporte generado"), error=False
                )

            self._refrescar_tabla()
            self.page.update()

        threading.Thread(target=_worker, daemon=True).start()

    def _exportar(self, formato: str):
        if not self._tipo_seleccionado:
            self._mostrar_snack("⚠️ Selecciona un tipo de reporte.", error=True)
            return

        def _worker():
            anio = int(self._dropdown_anio.value) if self._dropdown_anio.value else None
            mes_raw = self._dropdown_mes.value
            mes = int(mes_raw) if mes_raw and mes_raw.isdigit() else None

            resultado = ReportesService.exportar(
                self._tipo_seleccionado, formato=formato, anio=anio, mes=mes
            )

            self._mostrar_snack(
                resultado.get("message", ""), error=not resultado.get("success")
            )
            self.page.update()

        threading.Thread(target=_worker, daemon=True).start()

    def _refrescar_tabla(self):
        if not self._filas:
            self._tabla.columns = [ft.DataColumn(ft.Text("Sin datos"))]
            self._tabla.rows = []
            self._contador_label.value = "0 registros"
            return

        columnas = [ft.DataColumn(ft.Text(k)) for k in self._filas[0].keys()]
        filas = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(v) if v is not None else "—"))
                    for v in f.values()
                ]
            )
            for f in self._filas
        ]

        self._tabla.columns = columnas
        self._tabla.rows = filas
        self._contador_label.value = f"{len(filas)} registros"

    # ============================================================
    # FEEDBACK
    # ============================================================
    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        self.page.update()
