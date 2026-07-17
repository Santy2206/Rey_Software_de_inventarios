"""
Vista de Movimientos.

Permite registrar entradas, salidas y bajas de productos, y consultar
el historial de movimientos. Conectada a BodegasService, ProductosService
y MovimientosService (que a su vez deja constancia en la bitácora).

Sigue el mismo patrón que bodegas_view.py / productos_view.py:
  - Función pública MovimientosView() que envuelve la clase privada.
  - Clase _MovimientosView hereda de ft.Container.
  - Carga de datos y escrituras corren en hilos de fondo (threading).
  - SnackBar se registra en page.overlay desde did_mount().
"""

import threading
import flet as ft
from datetime import datetime

from src.services.movimientos_service import MovimientosService
from src.services.bodegas_service import BodegasService
from src.services.productos_service import ProductosService
from src.services.auth_service import get_usuario_id

_COLOR_TIPO = {
    "Entrada": ("#DCFCE7", "#15803D"),
    "Salida": ("#FEE2E2", "#B91C1C"),
    "Baja": ("#FEF3C7", "#B45309"),
}


def MovimientosView():
    return ft.Column(controls=[_MovimientosView()])


class _MovimientosView(ft.Container):

    def __init__(self):
        super().__init__()

        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        # ── Estado interno ──────────────────────────────────────────
        self._bodegas: list[dict] = []
        self._productos: list[dict] = []
        self._movimientos: list[dict] = []

        self._snackbar = ft.SnackBar(content=ft.Text(""), show_close_icon=True)

        self.content = ft.Column(
            spacing=0,
            expand=True,
            controls=[
                self.header_section(),
                ft.Container(height=20),
                self.form_section(),
                ft.Container(height=20),
                self.history_section(),
            ],
        )

    # ============================================================
    # LIFECYCLE
    # ============================================================

    def did_mount(self):
        self.page.overlay.append(self._snackbar)
        self.page.update()
        threading.Thread(target=self._cargar_datos_iniciales, daemon=True).start()

    def _cargar_datos_iniciales(self):
        res_bodegas = BodegasService.get_all()
        if res_bodegas["success"]:
            self._bodegas = res_bodegas["data"]
            self.bodega.options = [
                ft.DropdownOption(key=b["id"], text=b["nombre"]) for b in self._bodegas
            ]
            self.filtro_bodega.options = [ft.DropdownOption("Todas")] + [
                ft.DropdownOption(b["nombre"]) for b in self._bodegas
            ]

        res_productos = ProductosService.get_all()
        if res_productos["success"]:
            self._productos = res_productos["data"]
            self.producto.options = [
                ft.DropdownOption(key=p["id"], text=p["nombre"])
                for p in self._productos
            ]

        self._cargar_historial()
        self.page.update()

    def _cargar_historial(self):
        resultado = MovimientosService.get_all()
        self._movimientos = resultado["data"] if resultado["success"] else []
        self._refrescar_tabla()
        self._actualizar_contador()

    # ============================================================
    # HEADER
    # ============================================================

    def header_section(self):

        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            "Movimientos",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="#222",
                        ),
                        ft.Text(
                            "Entradas, salidas y bajas de productos",
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

    # ============================================================
    # FORMULARIO
    # ============================================================

    def form_section(self):

        self.tipo = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            on_change=self.actualizar_tipo,
            tabs=[
                ft.Tab(text="Entrada", icon=ft.Icons.DOWNLOAD),
                ft.Tab(text="Salida", icon=ft.Icons.UPLOAD),
                ft.Tab(text="Baja", icon=ft.Icons.DELETE),
            ],
        )

        self.bodega = ft.Dropdown(
            label="Bodega *",
            expand=True,
            options=[],
        )

        self.producto = ft.Dropdown(
            label="Producto *",
            expand=True,
            options=[],
        )

        self.cantidad = ft.TextField(
            label="Cantidad *",
            expand=True,
        )

        self.fecha = ft.TextField(
            label="Fecha",
            value=datetime.now().strftime("%d/%m/%Y"),
            read_only=True,
            expand=True,
        )

        self.notas = ft.TextField(
            label="Notas",
            multiline=True,
            min_lines=3,
            max_lines=3,
        )

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
                    self.tipo,
                    ft.Row(
                        spacing=15,
                        controls=[
                            self.bodega,
                            self.producto,
                        ],
                    ),
                    ft.Row(
                        spacing=15,
                        controls=[
                            self.cantidad,
                            self.fecha,
                        ],
                    ),
                    self.notas,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[self.crear_boton()],
                    ),
                ],
            ),
        )

    def crear_boton(self):
        self.boton_registrar = ft.ElevatedButton(
            "Registrar Entrada",
            icon=ft.Icons.DOWNLOAD,
            bgcolor="#16A34A",
            color="white",
            height=45,
            on_click=self.registrar_movimiento,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        )
        return self.boton_registrar

    def actualizar_tipo(self, e=None):
        indice = self.tipo.selected_index

        if indice == 0:
            self.boton_registrar.text = "Registrar Entrada"
            self.boton_registrar.icon = ft.Icons.DOWNLOAD
            self.boton_registrar.bgcolor = "#16A34A"
        elif indice == 1:
            self.boton_registrar.text = "Registrar Salida"
            self.boton_registrar.icon = ft.Icons.UPLOAD
            self.boton_registrar.bgcolor = "#DC2626"
        else:
            self.boton_registrar.text = "Registrar Baja"
            self.boton_registrar.icon = ft.Icons.DELETE
            self.boton_registrar.bgcolor = "#D97706"

        self.update()

    # ============================================================
    # REGISTRAR MOVIMIENTO
    # ============================================================

    def registrar_movimiento(self, e):

        bodega_id = self.bodega.value
        producto_id = self.producto.value
        cantidad_raw = (self.cantidad.value or "").strip()

        if not bodega_id or not producto_id or not cantidad_raw:
            self._mostrar_snack(
                "⚠️ Bodega, producto y cantidad son obligatorios.", error=True
            )
            return

        try:
            cantidad = int(cantidad_raw)
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            self._mostrar_snack(
                "⚠️ La cantidad debe ser un número entero mayor a 0.", error=True
            )
            return

        usuario_id = get_usuario_id()
        if not usuario_id:
            self._mostrar_snack(
                "⚠️ No se encontró un usuario válido para registrar el movimiento.",
                error=True,
            )
            return

        motivo = (self.notas.value or "").strip()
        indice = self.tipo.selected_index

        def _worker():
            if indice == 0:
                result = MovimientosService.registrar_entrada(
                    producto_id, bodega_id, cantidad, motivo, usuario_id
                )
            elif indice == 1:
                result = MovimientosService.registrar_salida(
                    producto_id, bodega_id, cantidad, motivo, usuario_id
                )
            else:
                result = MovimientosService.registrar_baja(
                    producto_id, bodega_id, cantidad, motivo, usuario_id
                )

            self._mostrar_snack(result["message"], error=not result["success"])

            if result["success"]:
                self.limpiar_formulario()
                self._cargar_historial()
                self.page.update()

        threading.Thread(target=_worker, daemon=True).start()

    def limpiar_formulario(self):
        self.bodega.value = None
        self.producto.value = None
        self.cantidad.value = ""
        self.notas.value = ""

    # ============================================================
    # HISTORIAL
    # ============================================================

    def history_section(self):

        self.filtro_tipo = ft.Dropdown(
            width=180,
            label="Tipo",
            value="Todos",
            on_change=self._aplicar_filtros,
            options=[
                ft.DropdownOption("Todos"),
                ft.DropdownOption("Entrada"),
                ft.DropdownOption("Salida"),
                ft.DropdownOption("Baja"),
            ],
        )

        self.filtro_bodega = ft.Dropdown(
            width=200,
            label="Bodega",
            value="Todas",
            on_change=self._aplicar_filtros,
            options=[ft.DropdownOption("Todas")],
        )

        self.buscar = ft.TextField(
            on_change=self._aplicar_filtros,
            expand=True,
            hint_text="Buscar producto...",
            prefix_icon=ft.Icons.SEARCH,
        )

        self.tabla = ft.DataTable(
            expand=True,
            border=ft.border.all(1, "#eeeeee"),
            border_radius=10,
            vertical_lines=ft.BorderSide(1, "#eeeeee"),
            horizontal_lines=ft.BorderSide(1, "#eeeeee"),
            heading_row_color="#fafafa",
            columns=[
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Tipo")),
                ft.DataColumn(ft.Text("Bodega")),
                ft.DataColumn(ft.Text("Producto")),
                ft.DataColumn(ft.Text("Cantidad")),
                ft.DataColumn(ft.Text("Usuario")),
            ],
            rows=[],
        )

        self.lbl_registros = ft.Text(
            "0 registros",
            color="#4338CA",
            weight=ft.FontWeight.BOLD,
        )

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
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(
                                        "Historial de Movimientos",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        "Consulta todos los movimientos registrados",
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
                                            ft.Icons.LIST_ALT, color="#4338CA", size=16
                                        ),
                                        self.lbl_registros,
                                    ],
                                ),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            self.buscar,
                            self.filtro_tipo,
                            self.filtro_bodega,
                        ],
                    ),
                    ft.Divider(),
                    self.tabla,
                ],
            ),
        )

    def _actualizar_contador(self):
        self.lbl_registros.value = f"{len(self.tabla.rows)} registros"

    def _refrescar_tabla(self):
        self.tabla.rows = [self._crear_fila_movimiento(m) for m in self._movimientos]

    def _crear_fila_movimiento(self, m: dict):
        tipo_db = m.get("tipo", "")
        motivo = m.get("motivo") or ""

        if tipo_db == "ingreso":
            tipo_label = "Entrada"
        elif motivo.upper().startswith("BAJA"):
            tipo_label = "Baja"
        else:
            tipo_label = "Salida"

        color, texto = _COLOR_TIPO[tipo_label]

        fecha = m.get("fecha")
        fecha_str = (
            fecha.strftime("%d/%m/%Y")
            if hasattr(fecha, "strftime")
            else str(fecha or "—")
        )

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(fecha_str)),
                ft.DataCell(
                    ft.Container(
                        bgcolor=color,
                        border_radius=20,
                        padding=6,
                        content=ft.Text(
                            tipo_label, color=texto, weight=ft.FontWeight.BOLD
                        ),
                    )
                ),
                ft.DataCell(ft.Text(m.get("bodega_nombre") or "—")),
                ft.DataCell(ft.Text(m.get("producto_nombre") or "—")),
                ft.DataCell(ft.Text(str(m.get("cantidad", "")))),
                ft.DataCell(ft.Text(m.get("usuario_nombre") or "—")),
            ]
        )

    # ============================================================
    # FILTROS (búsqueda + tipo + bodega, combinados)
    # ============================================================

    def _aplicar_filtros(self, e=None):
        texto = (self.buscar.value or "").lower()
        tipo_sel = self.filtro_tipo.value
        bodega_sel = self.filtro_bodega.value

        for fila in self.tabla.rows:
            producto = fila.cells[3].content.value.lower()
            tipo_fila = fila.cells[1].content.content.value
            bodega_fila = fila.cells[2].content.value

            visible = texto in producto
            if tipo_sel and tipo_sel != "Todos":
                visible = visible and tipo_fila == tipo_sel
            if bodega_sel and bodega_sel != "Todas":
                visible = visible and bodega_fila == bodega_sel

            fila.visible = visible

        self.update()

    # ============================================================
    # FEEDBACK
    # ============================================================

    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        self.page.update()
