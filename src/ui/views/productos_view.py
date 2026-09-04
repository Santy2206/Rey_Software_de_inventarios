"""
Vista de Productos.

Permite listar, crear, editar y eliminar productos. Cada producto
pertenece a una bodega y tiene nombre, descripción, SKU, precio y
stock_actual según el esquema real de la base de datos.

Sigue el mismo patrón que bodegas_view.py:
  - Función pública ProductosView() que envuelve la clase privada.
  - Clase _ProductosView hereda de ft.Container.
  - Carga de datos y escrituras corren en hilos de fondo (threading).
  - Dialog y SnackBar se registran en page.overlay desde did_mount().
  - Un solo page.update() al final de cada operación de carga.

Reglas:
    - SIN lógica de negocio — solo diseño e interacción de interfaz.
    - SIN llamadas directas a local_db, psycopg2 ni Supabase.
    - SIN ft.app() — esta vista es montada por dashboard_view.py.
"""

import threading
import flet as ft

from src.services.productos_service import ProductosService
from src.services.bodegas_service import BodegasService

_CARD_COLORS = ["#f5b400", "#c2185b", "#2563eb", "#16a34a", "#7c3aed"]


def ProductosView():
    return ft.Column(controls=[_ProductosView()])


class _ProductosView(ft.Container):

    def __init__(self):
        super().__init__()
        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        # ── Estado interno ───────────────────────────────────────────────────
        self._productos: list[dict] = []
        self._producto_editando: dict | None = None
        self._bodegas: list[dict] = []
        self._bodega_filtro: str | None = "todas"

        # ── Controles de texto actualizables ─────────────────────────────────
        self._total_text = ft.Text("…", size=16, weight=ft.FontWeight.BOLD)
        self._fecha_text = ft.Text("…", size=16, weight=ft.FontWeight.BOLD)

        # ── Filtro por bodega ────────────────────────────────────────────────
        self._filtro_bodega = ft.Dropdown(
            label="Filtrar por bodega",
            width=300,
            options=[ft.DropdownOption(key="todas", text="Todas")],
            on_change=self._aplicar_filtro,
        )

        # ── Fila de tarjetas + indicador de carga ───────────────────────────
        self._cards_row = ft.Row(spacing=15, wrap=True)
        self._loading_ring = ft.ProgressRing(width=32, height=32, visible=True)
        self._cards_area = ft.Column(
            controls=[
                ft.Row(
                    [self._loading_ring],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                self._cards_row,
            ]
        )

        # Campos del formulario
        self._campo_nombre = ft.TextField(
            label="Nombre del producto *",
            hint_text='Ej: "Perfume Floral 100ml"',
            border_radius=10,
        )
        self._campo_descripcion = ft.TextField(
            label="Descripción",
            hint_text="Detalle del producto (opcional)",
            border_radius=10,
        )
        self._campo_sku = ft.TextField(
            label="SKU / Referencia *",
            hint_text="Ej: PF-001",
            border_radius=10,
        )
        self._campo_precio = ft.TextField(
            label="Precio *",
            hint_text="Ej: 25000",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
        )
        self._campo_stock = ft.TextField(
            label="Stock inicial *",
            value="0",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
        )
        self._campo_bodega = ft.Dropdown(
            label="Bodega *",
            options=[],
            border_radius=10,
        )

        # ── Diálogo modal
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(""),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    self._campo_nombre,
                    self._campo_descripcion,
                    self._campo_sku,
                    self._campo_precio,
                    self._campo_stock,
                    self._campo_bodega,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo),
                ft.ElevatedButton(
                    "Guardar",
                    bgcolor="#9eff8f",
                    color="black",
                    on_click=self._guardar_producto,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # ── SnackBar
        self._snackbar = ft.SnackBar(
            content=ft.Text(""),
            show_close_icon=True,
        )

        # ── Layout principal ─────────────────────────────────────────────────
        self.content = ft.Column(
            controls=[
                self._header_section(),
                ft.Container(height=15),
                self._filtro_bodega,
                ft.Container(height=10),
                self._cards_area,
                ft.Container(height=20),
                self._bottom_section(),
            ],
            spacing=0,
            expand=True,
        )

    # ── Lifecycle hook ──────────────────────────────────────────────────────
    def did_mount(self):
        self.page.overlay.append(self._dialog)
        self.page.overlay.append(self._snackbar)
        self.page.update()
        threading.Thread(target=self._cargar_productos, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # Carga de datos (corre en Thread separado)
    # ─────────────────────────────────────────────────────────────────────────

    def _cargar_productos(self):
        res_bodegas = BodegasService.get_all()
        if res_bodegas.get("success"):
            self._bodegas = res_bodegas.get("data", [])
            self._campo_bodega.options = [
                ft.DropdownOption(key=b["id"], text=b["nombre"])
                for b in self._bodegas
            ]
            self._filtro_bodega.options = [
                ft.DropdownOption(key="todas", text="Todas")
            ] + [
                ft.DropdownOption(key=b["id"], text=b["nombre"])
                for b in self._bodegas
            ]

        if self._bodega_filtro and self._bodega_filtro != "todas":
            res = ProductosService.get_by_bodega(self._bodega_filtro)
        else:
            res = ProductosService.get_all()

        # Ocultar spinner
        self._loading_ring.visible = False

        if res.get("success"):
            self._productos = res.get("data", [])
        else:
            self._productos = []
            if "Error" in res.get("message", ""):
                self._mostrar_snack(res["message"], error=True)

        # Normaliza el nombre de la bodega para las tarjetas
        bodegas_por_id = {b["id"]: b["nombre"] for b in self._bodegas}
        for p in self._productos:
            p["bodega_nombre"] = bodegas_por_id.get(p.get("bodega_id"), "—")

        self._refrescar_cards()
        self._actualizar_stats()
        self.page.update()  # UN solo update al final

    # ─────────────────────────────────────────────────────────────────────────
    # Construcción de tarjetas dinámicas
    # ─────────────────────────────────────────────────────────────────────────

    def _refrescar_cards(self):
        self._cards_row.controls.clear()
        for i, producto in enumerate(self._productos):
            color = _CARD_COLORS[i % len(_CARD_COLORS)]
            self._cards_row.controls.append(self._producto_card(producto, color))

    def _actualizar_stats(self):
        from datetime import datetime

        self._total_text.value = str(len(self._productos))
        self._fecha_text.value = datetime.now().strftime("%d/%m/%Y %I:%M %p")

    # ─────────────────────────────────────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────────────────────────────────────

    def _header_section(self):
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            "Productos",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="#222",
                        ),
                        ft.Text(
                            "Gestiona los productos del inventario",
                            size=12,
                            color="grey",
                        ),
                    ],
                ),
                ft.ElevatedButton(
                    "Crear Producto",
                    icon=ft.Icons.ADD,
                    bgcolor="#9eff8f",
                    color="black",
                    on_click=self._abrir_dialogo_crear,
                ),
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Tarjeta individual de producto
    # ─────────────────────────────────────────────────────────────────────────

    def _producto_card(self, producto: dict, color: str):
        nombre = producto.get("nombre", "Sin nombre")
        sku = producto.get("sku", "—")
        bodega = producto.get("bodega_nombre", "—")
        stock = producto.get("stock_actual", 0)
        precio = producto.get("precio", 0)

        return ft.Container(
            width=280,
            bgcolor="white",
            border_radius=15,
            padding=15,
            shadow=ft.BoxShadow(
                spread_radius=1, blur_radius=8, color=ft.Colors.BLACK12
            ),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Container(
                                        width=40,
                                        height=40,
                                        border_radius=10,
                                        bgcolor="#f0f0f0",
                                        alignment=ft.Alignment(0, 0),
                                        content=ft.Icon(
                                            ft.Icons.INVENTORY_2, color=color
                                        ),
                                    ),
                                    ft.Column(
                                        spacing=0,
                                        controls=[
                                            ft.Text(
                                                nombre,
                                                weight=ft.FontWeight.BOLD,
                                                size=14,
                                            ),
                                            ft.Text(
                                                f"SKU: {sku}",
                                                size=11,
                                                color="grey",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Text(f"Bodega: {bodega}", size=12, color="grey"),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Text(
                                f"Stock: {stock}",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                f"${precio}",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=color,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.FilledButton(
                                "Editar",
                                icon=ft.Icons.EDIT,
                                bgcolor=color,
                                color="white",
                                expand=True,
                                on_click=lambda e, p=producto: self._abrir_dialogo_editar(
                                    p
                                ),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color="red",
                                tooltip="Eliminar producto",
                                on_click=lambda e, pid=producto["id"], nom=nombre: self._eliminar_producto(
                                    pid, nom
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Panel inferior
    # ─────────────────────────────────────────────────────────────────────────

    def _bottom_section(self):
        return ft.Row(
            spacing=15,
            controls=[
                self._info_card(
                    "Productos registrados", self._total_text, "#ffe8a3"
                ),
                ft.Container(height=10),
                self._info_card(
                    "Última actualización", self._fecha_text, "#dcecff"
                ),
            ],
        )

    def _info_card(self, title: str, value_widget: ft.Text, color: str):
        return ft.Container(
            bgcolor="white",
            border_radius=15,
            padding=15,
            shadow=ft.BoxShadow(
                spread_radius=1, blur_radius=6, color=ft.Colors.BLACK12
            ),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(title, size=12, color="grey"),
                            value_widget,
                        ],
                    ),
                    ft.Container(
                        width=35, height=35, border_radius=10, bgcolor=color
                    ),
                ],
            ),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Filtro
    # ─────────────────────────────────────────────────────────────────────────

    def _aplicar_filtro(self, e=None):
        self._bodega_filtro = self._filtro_bodega.value
        self._loading_ring.visible = True
        self._cards_row.controls.clear()
        self.page.update()
        threading.Thread(target=self._cargar_productos, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # Diálogos
    # ─────────────────────────────────────────────────────────────────────────

    def _abrir_dialogo_crear(self, e=None):
        self._producto_editando = None
        self._campo_nombre.value = ""
        self._campo_descripcion.value = ""
        self._campo_sku.value = ""
        self._campo_precio.value = ""
        self._campo_stock.value = "0"
        self._campo_stock.disabled = False
        self._campo_bodega.value = None
        self._dialog.title = ft.Text("Nuevo Producto")
        self._dialog.open = True
        self.page.update()

    def _abrir_dialogo_editar(self, producto: dict):
        self._producto_editando = producto
        self._campo_nombre.value = producto.get("nombre", "")
        self._campo_descripcion.value = producto.get("descripcion", "")
        self._campo_sku.value = producto.get("sku", "")
        self._campo_precio.value = str(producto.get("precio", ""))
        # stock_actual no se edita desde este diálogo — se muestra solo lectura
        self._campo_stock.value = str(producto.get("stock_actual", "0"))
        self._campo_stock.disabled = True
        self._campo_bodega.value = producto.get("bodega_id")
        self._dialog.title = ft.Text(f"Editar: {producto.get('nombre')}")
        self._dialog.open = True
        self.page.update()

    def _cerrar_dialogo(self, e=None):
        self._dialog.open = False
        self.page.update()

    # ─────────────────────────────────────────────────────────────────────────
    # CRUD — delegan al servicio, luego recargan en background
    # ─────────────────────────────────────────────────────────────────────────

    def _guardar_producto(self, e):
        nombre = (self._campo_nombre.value or "").strip()
        descripcion = (self._campo_descripcion.value or "").strip()
        sku = (self._campo_sku.value or "").strip()
        precio_raw = (self._campo_precio.value or "").strip()
        stock_raw = (self._campo_stock.value or "").strip()
        bodega_id = self._campo_bodega.value

        if not nombre or not sku or not bodega_id:
            self._mostrar_snack(
                "⚠️ Nombre, SKU y Bodega son obligatorios.", error=True
            )
            self.page.update()
            return

        try:
            precio = float(precio_raw) if precio_raw else 0.0
            stock = int(stock_raw) if stock_raw else 0
        except ValueError:
            self._mostrar_snack(
                "⚠️ Precio y Stock deben ser valores numéricos.", error=True
            )
            self.page.update()
            return

        self._cerrar_dialogo()

        def _worker():
            if self._producto_editando is None:
                result = ProductosService.create(
                    nombre=nombre,
                    descripcion=descripcion,
                    sku=sku,
                    precio=precio,
                    stock_actual=stock,
                    bodega_id=bodega_id,
                )
            else:
                result = ProductosService.update(
                    producto_id=self._producto_editando["id"],
                    nombre=nombre,
                    descripcion=descripcion,
                    sku=sku,
                    precio=precio,
                    bodega_id=bodega_id,
                )
            self._mostrar_snack(
                result.get("message", ""), error=not result.get("success")
            )
            if result.get("success"):
                self._loading_ring.visible = True
                self.page.update()
                self._cargar_productos()

        threading.Thread(target=_worker, daemon=True).start()

    def _eliminar_producto(self, producto_id: str, nombre: str):
        def _worker():
            result = ProductosService.delete(producto_id=producto_id)
            self._mostrar_snack(
                result.get("message", ""), error=not result.get("success")
            )
            if result.get("success"):
                self._loading_ring.visible = True
                self.page.update()
                self._cargar_productos()

        threading.Thread(target=_worker, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # Feedback
    # ─────────────────────────────────────────────────────────────────────────

    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        self.page.update()
