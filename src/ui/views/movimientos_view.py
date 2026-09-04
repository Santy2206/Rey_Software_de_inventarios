"""
Vista de Movimientos.

Permite registrar entradas, salidas, ajustes y bajas de productos, y
consultar el historial de movimientos con filtros por producto y rango
de fecha.

Sigue el mismo patrón que bodegas_view.py:
  - Función pública MovimientosView() que envuelve la clase privada.
  - Clase _MovimientosView hereda de ft.Container.
  - Carga de datos y escrituras corren en hilos de fondo (threading).
  - SnackBar se registra en page.overlay desde did_mount().
  - Un solo page.update() al final de cada operación de carga.

Reglas:
    - SIN lógica de negocio — solo diseño e interacción de interfaz.
    - SIN llamadas directas a local_db, psycopg2 ni Supabase.
    - SIN ft.app() — esta vista es montada por dashboard_view.py.
"""

import threading
from datetime import datetime, date
from decimal import Decimal

import flet as ft

from src.services.movimientos_service import MovimientosService
from src.services.bodegas_service import BodegasService
from src.services.productos_service import ProductosService
from src.services.auth_service import AuthService

_COLOR_TIPO = {
    "Entrada": ("#DCFCE7", "#15803D"),
    "Salida": ("#FEE2E2", "#B91C1C"),
    "Transferencia": ("#E0E7FF", "#4338CA"),
}

# El CHECK CONSTRAINT de la base de datos solo permite ingreso/egreso/transferencia.
# La UI sigue llamándolos con nombres de negocio: Entrada, Salida, Ajuste, Baja.
_TIPO_DB_A_LABEL = {
    "ingreso": "Entrada",
    "egreso": "Salida",
    "transferencia": "Transferencia",
}


def MovimientosView():
    return ft.Column(controls=[_MovimientosView()])


class _MovimientosView(ft.Container):

    def __init__(self):
        super().__init__()

        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        # ── Estado interno ──────────────────────────────────────────────
        self._bodegas: list[dict] = []
        self._productos: list[dict] = []
        self._movimientos: list[dict] = []

        self._snackbar = ft.SnackBar(content=ft.Text(""), show_close_icon=True)

        # ── Filtros de historial ────────────────────────────────────────
        self._filtro_producto = ft.Dropdown(
            label="Producto",
            width=250,
            options=[ft.DropdownOption(key="todas", text="Todas")],
            on_change=self._aplicar_filtros,
        )
        self._filtro_fecha_inicio = ft.TextField(
            label="Desde",
            hint_text="DD/MM/AAAA",
            width=140,
            on_change=self._aplicar_filtros,
        )
        self._filtro_fecha_fin = ft.TextField(
            label="Hasta",
            hint_text="DD/MM/AAAA",
            width=140,
            on_change=self._aplicar_filtros,
        )

        # ── Contadores ──────────────────────────────────────────────────
        self._lbl_registros = ft.Text(
            "0 registros", color="#4338CA", weight=ft.FontWeight.BOLD
        )

        # ── Tabla de historial ──────────────────────────────────────────
        self._tabla = ft.DataTable(
            expand=True,
            border=ft.Border.all(1, "#eeeeee"),
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
                ft.DataColumn(ft.Text("Motivo")),
                ft.DataColumn(ft.Text("Usuario")),
            ],
            rows=[],
        )

        # ── Layout principal ────────────────────────────────────────────
        self.content = ft.Column(
            spacing=0,
            expand=True,
            controls=[
                self._header_section(),
                ft.Container(height=20),
                self._form_section(),
                ft.Container(height=20),
                self._history_section(),
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
        if res_bodegas.get("success"):
            self._bodegas = res_bodegas.get("data", [])
            self.bodega.options = [
                ft.DropdownOption(key=b["id"], text=b["nombre"])
                for b in self._bodegas
            ]

        res_productos = ProductosService.get_all()
        if res_productos.get("success"):
            self._productos = res_productos.get("data", [])
            self.producto.options = [
                ft.DropdownOption(key=p["id"], text=p["nombre"])
                for p in self._productos
            ]
            self._filtro_producto.options = [
                ft.DropdownOption(key="todas", text="Todas")
            ] + [
                ft.DropdownOption(key=p["id"], text=p["nombre"])
                for p in self._productos
            ]

        self._cargar_historial()
        self.page.update()

    def _cargar_historial(self):
        resultado = MovimientosService.get_all()
        if resultado.get("success"):
            self._movimientos = resultado.get("data", [])
        else:
            self._movimientos = []
            if "Error" in resultado.get("message", ""):
                self._mostrar_snack(resultado["message"], error=True)

        self._aplicar_filtros()

    # ============================================================
    # HEADER
    # ============================================================

    def _header_section(self):
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
                            "Entradas, salidas, ajustes y bajas de productos",
                            size=12,
                            color="grey",
                        ),
                    ],
                ),
                ft.Container(
                    bgcolor="#E8FFF0",
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    content=ft.Row(
                        spacing=5,
                        controls=[
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE,
                                color="green",
                                size=16,
                            ),
                            ft.Text(
                                "Online",
                                color="green",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                ),
            ],
        )

    # ============================================================
    # FORMULARIO
    # ============================================================

    def _form_section(self):
        self.tipo = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            on_change=self._actualizar_tipo,
            tabs=[
                ft.Tab(text="Entrada", icon=ft.Icons.DOWNLOAD),
                ft.Tab(text="Salida", icon=ft.Icons.UPLOAD),
                ft.Tab(text="Ajuste", icon=ft.Icons.TUNE),
                ft.Tab(text="Baja", icon=ft.Icons.DELETE),
            ],
        )

        self.bodega = ft.Dropdown(label="Bodega *", expand=True, options=[])
        self.producto = ft.Dropdown(label="Producto *", expand=True, options=[])
        self.cantidad = ft.TextField(
            label="Cantidad *",
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.motivo = ft.TextField(
            label="Motivo",
            multiline=True,
            min_lines=2,
            max_lines=2,
        )

        self.boton_registrar = ft.ElevatedButton(
            "Registrar Entrada",
            icon=ft.Icons.DOWNLOAD,
            bgcolor="#16A34A",
            color="white",
            height=45,
            on_click=self._registrar_movimiento,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        )

        return ft.Container(
            bgcolor="white",
            border_radius=15,
            padding=20,
            content=ft.Column(
                spacing=20,
                controls=[
                    self.tipo,
                    ft.Row(spacing=15, controls=[self.bodega, self.producto]),
                    self.cantidad,
                    self.motivo,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[self.boton_registrar],
                    ),
                ],
            ),
        )

    def _actualizar_tipo(self, e=None):
        indice = self.tipo.selected_index

        textos = [
            ("Registrar Entrada", ft.Icons.DOWNLOAD, "#16A34A"),
            ("Registrar Salida", ft.Icons.UPLOAD, "#DC2626"),
            ("Registrar Ajuste", ft.Icons.TUNE, "#D97706"),
            ("Registrar Baja", ft.Icons.DELETE, "#7C2D12"),
        ]
        texto, icono, color = textos[indice]

        self.boton_registrar.text = texto
        self.boton_registrar.icon = icono
        self.boton_registrar.bgcolor = color
        self.update()

    # ============================================================
    # REGISTRAR MOVIMIENTO
    # ============================================================

    def _registrar_movimiento(self, e):
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
                "⚠️ La cantidad debe ser un número entero mayor a 0.",
                error=True,
            )
            return

        usuario_id = AuthService.get_usuario_id()
        if not usuario_id:
            self._mostrar_snack(
                "⚠️ No se encontró un usuario válido para registrar el movimiento.",
                error=True,
            )
            return

        motivo = (self.motivo.value or "").strip()
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
            elif indice == 2:
                result = MovimientosService.registrar_ajuste(
                    producto_id, bodega_id, cantidad, motivo, usuario_id
                )
            else:
                result = MovimientosService.registrar_baja(
                    producto_id, bodega_id, cantidad, motivo, usuario_id
                )

            self._mostrar_snack(result.get("message", ""), error=not result.get("success"))

            if result.get("success"):
                self._limpiar_formulario()
                self._cargar_historial()

        threading.Thread(target=_worker, daemon=True).start()

    def _limpiar_formulario(self):
        self.bodega.value = None
        self.producto.value = None
        self.cantidad.value = ""
        self.motivo.value = ""

    # ============================================================
    # HISTORIAL
    # ============================================================

    def _history_section(self):
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
                                            ft.Icons.LIST_ALT,
                                            color="#4338CA",
                                            size=16,
                                        ),
                                        self._lbl_registros,
                                    ],
                                ),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        alignment=ft.MainAxisAlignment.START,
                        controls=[
                            self._filtro_producto,
                            self._filtro_fecha_inicio,
                            self._filtro_fecha_fin,
                        ],
                    ),
                    ft.Divider(),
                    self._tabla,
                ],
            ),
        )

    def _actualizar_contador(self):
        self._lbl_registros.value = f"{len(self._tabla.rows)} registros"

    def _refrescar_tabla(self, movimientos: list[dict]):
        self._tabla.rows = [
            self._crear_fila_movimiento(m) for m in movimientos
        ]

    def _crear_fila_movimiento(self, m: dict):
        tipo_db = (m.get("tipo") or "").lower()
        tipo_label = _TIPO_DB_A_LABEL.get(tipo_db, tipo_db)
        color, texto = _COLOR_TIPO.get(tipo_label, ("#E0E7FF", "#4338CA"))

        fecha = m.get("fecha")
        if isinstance(fecha, str):
            fecha_str = fecha
        elif hasattr(fecha, "strftime"):
            fecha_str = fecha.strftime("%d/%m/%Y %H:%M")
        else:
            fecha_str = str(fecha or "—")

        producto_nombre = m.get("producto_nombre") or "—"
        bodega_nombre = m.get("bodega_nombre") or "—"
        usuario_nombre = m.get("usuario_name") or m.get("usuario_id") or "—"

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(fecha_str)),
                ft.DataCell(
                    ft.Container(
                        bgcolor=color,
                        border_radius=20,
                        padding=6,
                        content=ft.Text(
                            tipo_label,
                            color=texto,
                            weight=ft.FontWeight.BOLD,
                        ),
                    )
                ),
                ft.DataCell(ft.Text(bodega_nombre)),
                ft.DataCell(ft.Text(producto_nombre)),
                ft.DataCell(ft.Text(str(m.get("cantidad", "")))),
                ft.DataCell(ft.Text(m.get("motivo") or "—")),
                ft.DataCell(ft.Text(usuario_nombre)),
            ]
        )

    # ============================================================
    # FILTROS (producto + rango de fecha)
    # ============================================================

    def _aplicar_filtros(self, e=None):
        producto_sel = self._filtro_producto.value
        inicio_str = (self._filtro_fecha_inicio.value or "").strip()
        fin_str = (self._filtro_fecha_fin.value or "").strip()

        inicio = self._parse_fecha(inicio_str)
        fin = self._parse_fecha(fin_str)

        filtrados = []
        for m in self._movimientos:
            if producto_sel and producto_sel != "todas":
                if m.get("producto_id") != producto_sel:
                    continue

            fecha = m.get("fecha")
            if inicio or fin:
                if not hasattr(fecha, "date"):
                    continue
                m_date = fecha.date()
                if inicio and m_date < inicio:
                    continue
                if fin and m_date > fin:
                    continue

            filtrados.append(m)

        self._refrescar_tabla(filtrados)
        self._actualizar_contador()
        self.page.update()

    def _parse_fecha(self, s: str) -> date | None:
        if not s:
            return None
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except ValueError:
            return None

    # ============================================================
    # FEEDBACK
    # ============================================================

    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        self.page.update()
