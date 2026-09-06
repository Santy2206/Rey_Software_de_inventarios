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

import os
import asyncio
import re
import subprocess
import tempfile
import threading
import flet as ft

from src.services.auth_service import AuthService
from src.services.productos_service import ProductosService
from src.services.bodegas_service import BodegasService
from src.ui.components.status_header import StatusHeader
from src.ui.components.page_header import PageHeader


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
            on_select=self._aplicar_filtro,
        )

        # ── Tabla tipo Excel + indicador de carga ────────────────────────────
        self._loading_ring = ft.ProgressRing(width=32, height=32, visible=True)
        self._cards_area = ft.Column(
            controls=[
                ft.Row(
                    [self._loading_ring],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            ],
            spacing=10,
            expand=True,
        )

        # Campos del formulario
        self._campo_nombre = ft.TextField(
            label="Nombre del producto *",
            hint_text='Ej: "Perfume Floral 100ml"',
            border_radius=10,
        )
        self._campo_stock = ft.TextField(
            label="Stock",
            value="0",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
            disabled=True,
            visible=False,
        )
        self._campo_bodega = ft.Dropdown(
            label="Bodega *",
            options=[],
            border_radius=10,
            on_select=self._on_bodega_seleccionada,
        )
        self._campo_codigo = ft.TextField(
            label="Código de fragancia *",
            hint_text='Ej: "F-001"',
            border_radius=10,
            visible=False,
        )
        self._campo_precio = ft.TextField(
            label="Precio",
            hint_text="Ej: 150000",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
            visible=False,
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
                    self._campo_stock,
                    self._campo_bodega,
                    self._campo_codigo,
                    self._campo_precio,
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

        # ── Barra de estado
        self._status_header = StatusHeader()

        # Campos del diálogo de importación
        self._import_bodega = ft.Dropdown(
            label="Bodega destino *",
            options=[],
            border_radius=10,
        )
        self._import_ruta = ft.TextField(
            label="Ruta del archivo",
            hint_text="C:\\Users\\...\\productos.xlsx",
            border_radius=10,
            expand=True,
        )

        self._dialog_importar = ft.AlertDialog(
            modal=True,
            title=ft.Text("Importar productos desde Excel/CSV"),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    self._import_bodega,
                    ft.Row(
                        spacing=8,
                        controls=[
                            self._import_ruta,
                            ft.ElevatedButton(
                                "Examinar",
                                icon=ft.Icons.FOLDER_OPEN,
                                bgcolor="#2196F3",
                                color="white",
                                on_click=self._abrir_selector_archivo,
                            ),
                        ],
                    ),
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_importar),
                ft.ElevatedButton(
                    "Importar",
                    bgcolor="#2196F3",
                    color="white",
                    on_click=self._importar_excel,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # ── SnackBar
        self._snackbar = ft.SnackBar(
            content=ft.Text(""),
            show_close_icon=True,
        )

        # ── Diálogo de eliminación masiva
        self._eliminar_password = ft.TextField(
            label="Contraseña",
            password=True,
            can_reveal_password=True,
            border_radius=10,
        )
        self._eliminar_verificacion = ft.TextField(
            label="Escribe 'eliminar' para confirmar",
            border_radius=10,
        )

        self._dialog_eliminar_todos = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar todos los productos"),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    ft.Text(
                        "Esta acción borrará todos los productos, incluyendo sus movimientos y detalles de venta asociados.",
                        color="red",
                        size=13,
                    ),
                    self._eliminar_password,
                    self._eliminar_verificacion,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_eliminar_todos),
                ft.ElevatedButton(
                    "Eliminar todo",
                    icon=ft.Icons.DELETE_FOREVER,
                    bgcolor="#d32f2f",
                    color="white",
                    on_click=self._confirmar_eliminar_todos,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
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
        self.page.overlay.append(self._dialog_importar)
        self.page.overlay.append(self._dialog_eliminar_todos)
        self.page.overlay.append(self._snackbar)
        self.page.update()
        self._status_header.load(self.page)
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
            self._import_bodega.options = [
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

        self._ordenar_productos()
        self._refrescar_tabla()
        self._actualizar_stats()
        self.page.update()  # UN solo update al final

    # ─────────────────────────────────────────────────────────────────────────
    # Ordenamiento y construcción de la tabla tipo Excel
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _natural_key(texto: str):
        """Devuelve una clave de ordenamiento natural (109M antes que 83M)."""
        partes = []
        for token in re.split(r"(\d+)", texto or ""):
            if token.isdigit():
                partes.append(int(token))
            elif token:
                partes.append(token.lower())
        return tuple(partes)

    def _ordenar_productos(self):
        def _clave(p):
            es_fragancia = self._es_bodega_fragancia(p.get("bodega_id"))
            bodega = p.get("bodega_nombre", "").lower()
            if es_fragancia:
                return (bodega, self._natural_key(p.get("codigo") or ""))
            return (bodega, p.get("nombre", "").lower())

        self._productos.sort(key=_clave)

    def _es_bodega_venta(self, bodega_id: str | None) -> bool:
        """True si la bodega es una bodega de venta (nombre contiene VENTA)."""
        if not bodega_id:
            return False
        for b in self._bodegas:
            if b.get("id") == bodega_id:
                return "VENTA" in (b.get("nombre") or "").upper()
        return False

    def _refrescar_tabla(self):
        """Construye la(s) tabla(s): dos tablas lado a lado para fragancias M/F."""
        self._loading_ring.visible = False

        filtro_todas = not self._bodega_filtro or self._bodega_filtro == "todas"

        def _visible(p):
            # En "todas", las fragancias se muestran solo desde la bodega
            # de VENTA (el mismo código existe también en Fragancias Bodega
            # como stock maestro → evita verlo duplicado).
            if filtro_todas and self._es_bodega_fragancia(p.get("bodega_id")):
                return self._es_bodega_venta(p.get("bodega_id"))
            return True

        def _es_m(p):
            return self._es_bodega_fragancia(p.get("bodega_id")) and (
                (p.get("codigo") or "").upper().endswith("M")
            )

        def _es_f(p):
            return self._es_bodega_fragancia(p.get("bodega_id")) and (
                (p.get("codigo") or "").upper().endswith("F")
            )

        productos_m = [p for p in self._productos if _es_m(p) and _visible(p)]
        productos_f = [p for p in self._productos if _es_f(p) and _visible(p)]
        otros = [
            p for p in self._productos
            if not _es_m(p) and not _es_f(p) and _visible(p)
        ]

        nuevos_controles = []

        grupos = []
        if productos_m:
            grupos.append(
                ft.Column(
                    expand=1,
                    spacing=6,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Text(
                            "Masculino",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#222222",
                        ),
                        self._crear_data_table(productos_m),
                    ],
                )
            )
        if productos_f:
            grupos.append(
                ft.Column(
                    expand=1,
                    spacing=6,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Text(
                            "Femenino",
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color="#222222",
                        ),
                        self._crear_data_table(productos_f),
                    ],
                )
            )

        if grupos:
            nuevos_controles.append(
                ft.Row(
                    spacing=15,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=grupos,
                )
            )

        if otros:
            if grupos:
                nuevos_controles.append(
                    ft.Text(
                        "Otros productos",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color="#222222",
                    )
                )
            nuevos_controles.append(self._crear_data_table(otros))

        if not nuevos_controles:
            nuevos_controles.append(self._crear_data_table(self._productos))

        self._cards_area.controls = nuevos_controles

    def _crear_data_table(self, productos: list[dict]):
        return ft.DataTable(
            columns=[
                ft.DataColumn(
                    ft.Text(
                        "Código",
                        color="#222222",
                        weight=ft.FontWeight.BOLD,
                        size=14,
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "Nombre",
                        color="#222222",
                        weight=ft.FontWeight.BOLD,
                        size=14,
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "Bodega",
                        color="#222222",
                        weight=ft.FontWeight.BOLD,
                        size=14,
                    )
                ),
                ft.DataColumn(
                    ft.Text(
                        "Acciones",
                        color="#222222",
                        weight=ft.FontWeight.BOLD,
                        size=14,
                    )
                ),
            ],
            rows=[self._fila_producto(p) for p in productos],
            border=ft.border.all(1, "#e0e0e0"),
            border_radius=10,
            bgcolor="white",
            heading_row_color="#e0e0e0",
            data_text_style=ft.TextStyle(color="#222222", size=14),
            heading_text_style=ft.TextStyle(
                color="#222222", size=14, weight=ft.FontWeight.BOLD
            ),
            horizontal_lines=ft.border.BorderSide(1, "#e0e0e0"),
            vertical_lines=ft.border.BorderSide(1, "#e0e0e0"),
            divider_thickness=0,
            data_row_min_height=50,
        )

    def _fila_producto(self, producto: dict):
        nombre = producto.get("nombre", "Sin nombre")
        codigo = producto.get("codigo") or ""

        return ft.DataRow(
            cells=[
                ft.DataCell(
                    ft.Text(
                        codigo or "—",
                        color="#222222",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    )
                ),
                ft.DataCell(ft.Text(nombre, color="#222222", size=14)),
                ft.DataCell(
                    ft.Text(
                        producto.get("bodega_nombre") or "—",
                        color="#555555",
                        size=12,
                    )
                ),
                ft.DataCell(
                    ft.Row(
                        spacing=0,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.EDIT,
                                tooltip="Editar producto",
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
                    )
                ),
            ]
        )

    def _actualizar_stats(self):
        from datetime import datetime

        self._total_text.value = str(len(self._productos))
        self._fecha_text.value = datetime.now().strftime("%d/%m/%Y %I:%M %p")

    # ─────────────────────────────────────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────────────────────────────────────

    def _header_section(self):
        return PageHeader(
            title="Productos",
            subtitle="Gestiona los productos del inventario",
            status_control=self._status_header.control,
            action_buttons=[
                ft.ElevatedButton(
                    "Exportar Excel",
                    icon=ft.Icons.DOWNLOAD,
                    bgcolor="#2196F3",
                    color="white",
                    on_click=self._exportar_excel,
                ),
                ft.ElevatedButton(
                    "Importar Excel",
                    icon=ft.Icons.UPLOAD_FILE,
                    bgcolor="#2196F3",
                    color="white",
                    on_click=self._abrir_dialogo_importar,
                ),
                ft.ElevatedButton(
                    "Crear Producto",
                    icon=ft.Icons.ADD,
                    bgcolor="#9eff8f",
                    color="black",
                    on_click=self._abrir_dialogo_crear,
                ),
                ft.ElevatedButton(
                    "Eliminar todos",
                    icon=ft.Icons.DELETE_FOREVER,
                    bgcolor="#d32f2f",
                    color="white",
                    on_click=self._abrir_dialogo_eliminar_todos,
                ),
            ],
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
        self._cards_area.controls = [
            ft.Row(
                [self._loading_ring],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        ]
        self.page.update()
        threading.Thread(target=self._cargar_productos, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # Diálogos
    # ─────────────────────────────────────────────────────────────────────────

    def _es_bodega_fragancia(self, bodega_id: str | None) -> bool:
        if not bodega_id or not self._bodegas:
            return False
        for b in self._bodegas:
            if b.get("id") == bodega_id:
                nombre = (b.get("nombre") or "").lower()
                return "fragancia" in nombre
        return False

    def _on_bodega_seleccionada(self, e=None):
        """Muestra el campo código cuando la bodega es de fragancias."""
        bodega_id = self._campo_bodega.value
        es_fragancia = self._es_bodega_fragancia(bodega_id)
        self._campo_codigo.visible = es_fragancia
        if not es_fragancia:
            self._campo_codigo.value = ""
        try:
            self.page.update()
        except Exception:
            pass

    def _abrir_dialogo_crear(self, e=None):
        self._producto_editando = None
        self._campo_nombre.value = ""
        self._campo_stock.value = "0"
        self._campo_stock.disabled = True
        self._campo_stock.visible = False
        self._campo_bodega.value = None
        self._campo_codigo.value = ""
        self._campo_codigo.visible = False
        self._campo_precio.value = ""
        self._campo_precio.visible = False
        self._dialog.title = ft.Text("Nuevo Producto")
        self._dialog.open = True
        self.page.update()

    def _abrir_dialogo_editar(self, producto: dict):
        self._producto_editando = producto
        self._campo_nombre.value = producto.get("nombre", "")
        self._campo_codigo.value = producto.get("codigo") or ""
        # stock_actual se muestra solo lectura en edición
        self._campo_stock.value = str(producto.get("stock_actual", "0"))
        self._campo_stock.disabled = True
        self._campo_stock.visible = True
        self._campo_bodega.value = producto.get("bodega_id")
        self._campo_codigo.visible = self._es_bodega_fragancia(
            producto.get("bodega_id")
        )
        self._campo_precio.value = str(producto.get("precio") or "0")
        self._campo_precio.visible = True
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
        bodega_id = self._campo_bodega.value
        codigo = (
            (self._campo_codigo.value or "").strip()
            if self._campo_codigo.visible
            else None
        )

        if not nombre or not bodega_id:
            self._mostrar_snack(
                "⚠️ Nombre y Bodega son obligatorios.", error=True
            )
            self.page.update()
            return

        if self._campo_codigo.visible and not codigo:
            self._mostrar_snack(
                "⚠️ El código de fragancia es obligatorio para esta bodega.",
                error=True,
            )
            self.page.update()
            return

        self._cerrar_dialogo()

        def _worker():
            if self._producto_editando is None:
                result = ProductosService.create(
                    nombre=nombre,
                    bodega_id=bodega_id,
                    codigo=codigo,
                    stock_actual=0,
                )
            else:
                try:
                    precio = float(
                        (self._campo_precio.value or "0")
                        .replace("$", "")
                        .replace(",", "")
                        .strip()
                        or 0
                    )
                except ValueError:
                    precio = 0.0
                result = ProductosService.update(
                    producto_id=self._producto_editando["id"],
                    nombre=nombre,
                    bodega_id=bodega_id,
                    codigo=codigo,
                    precio=precio,
                )
            self._mostrar_snack(
                result.get("message", ""), error=not result.get("success")
            )
            if result.get("success"):
                self._loading_ring.visible = True
                self.page.update()
                self._cargar_productos()

        threading.Thread(target=_worker, daemon=True).start()

    def _abrir_dialogo_eliminar_todos(self, e=None):
        self._eliminar_password.value = ""
        self._eliminar_verificacion.value = ""
        self._dialog_eliminar_todos.open = True
        self.page.update()

    def _cerrar_dialogo_eliminar_todos(self, e=None):
        self._dialog_eliminar_todos.open = False
        self.page.update()

    def _confirmar_eliminar_todos(self, e=None):
        password = (self._eliminar_password.value or "").strip()
        verificacion = (self._eliminar_verificacion.value or "").strip().lower()

        if not password:
            self._mostrar_snack("Debe ingresar su contraseña", error=True)
            self.page.update()
            return

        if verificacion != "eliminar":
            self._mostrar_snack("Debe escribir 'eliminar' para confirmar", error=True)
            self.page.update()
            return

        resultado_verificacion = AuthService.verificar_password_sesion(password)
        if not resultado_verificacion.get("success"):
            self._mostrar_snack(
                resultado_verificacion.get("message", "Contraseña incorrecta"),
                error=True,
            )
            self.page.update()
            return

        self._cerrar_dialogo_eliminar_todos()

        def _worker():
            result = ProductosService.eliminar_todos()
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
    # Importación y exportación masiva desde Excel
    # ─────────────────────────────────────────────────────────────────────────

    def _exportar_excel(self, e=None):
        def _worker():
            bodega_id = (
                self._bodega_filtro
                if self._bodega_filtro and self._bodega_filtro != "todas"
                else None
            )
            result = ProductosService.exportar_excel(bodega_id=bodega_id)
            self.page.run_task(self._on_exportar_excel, result)

        threading.Thread(target=_worker, daemon=True).start()

    async def _on_exportar_excel(self, result: dict):
        if not result.get("success"):
            self._mostrar_snack(result.get("message", ""), error=True)
            return

        ruta = result.get("ruta", "")
        es_plantilla = result.get("es_plantilla", False)

        if self.page.web:
            base_url = self.page.url or "http://localhost:8550"
            if base_url.startswith("http"):
                url = base_url.rstrip("/") + "/downloads/productos_export.xlsx"
            else:
                url = "http://localhost:8550/downloads/productos_export.xlsx"
            try:
                await self.page.launch_url(url)
            except Exception:
                self._mostrar_snack(
                    "No se pudo abrir la URL de descarga.", error=True
                )
                return
        else:
            try:
                os.startfile(ruta)
            except Exception as ex:
                self._mostrar_snack(f"No se pudo abrir el archivo: {ex}", error=True)
                return

        mensaje = (
            "Plantilla descargada" if es_plantilla else "Productos exportados a Excel"
        )
        self._mostrar_snack(f"{mensaje}: {ruta}", error=False)

    def _abrir_dialogo_importar(self, e=None):
        self._import_bodega.value = None
        self._import_ruta.value = ""
        self._dialog_importar.open = True
        self.page.update()

    def _cerrar_dialogo_importar(self, e=None):
        self._dialog_importar.open = False
        self.page.update()

    def _abrir_selector_archivo(self, e=None):
        """Abre el explorador de archivos nativo."""
        if self.page.web:
            self.page.run_task(self._seleccionar_archivo)
            return

        threading.Thread(
            target=self._seleccionar_archivo_desktop, daemon=True
        ).start()

    def _seleccionar_archivo_desktop(self):
        """Selector nativo en escritorio (hilo aparte para no congelar la UI)."""
        try:
            comando = [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "$f = New-Object System.Windows.Forms.OpenFileDialog; "
                    "$f.Filter = 'Excel y CSV (*.xlsx,*.csv)|*.xlsx;*.csv|"
                    "Todos los archivos (*.*)|*.*'; "
                    "$f.Title = 'Seleccionar archivo de productos'; "
                    # Forma invisible TopMost como dueña: evita que el diálogo
                    # quede detrás de la ventana de la app.
                    "$owner = New-Object System.Windows.Forms.Form; "
                    "$owner.TopMost = $true; "
                    "$owner.StartPosition = 'CenterScreen'; "
                    "$owner.ShowInTaskbar = $false; "
                    "$owner.Width = 1; $owner.Height = 1; "
                    "$owner.Opacity = 0; "
                    "$owner.Show(); "
                    "if ($f.ShowDialog($owner) -eq 'OK') { "
                    "    Write-Output $f.FileName "
                    "}; "
                    "$owner.Close(); $owner.Dispose()"
                ),
            ]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
            )
            ruta = result.stdout.strip()
            if ruta:
                self._import_ruta.value = ruta
                if self.page:
                    self.page.update()
        except Exception as ex:
            self._mostrar_snack(f"No se pudo abrir el selector: {ex}", error=True)

    async def _seleccionar_archivo(self):
        # En Flet 0.84 FilePicker es un Service: debe registrarse en
        # page.services antes de usarse, si no falla con
        # "Control must be added to the page first".
        file_picker = ft.FilePicker()
        self.page.services.append(file_picker)
        self.page.update()
        try:
            archivos = await asyncio.wait_for(
                file_picker.pick_files(
                    dialog_title="Seleccionar archivo Excel o CSV",
                    allow_multiple=False,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["xlsx", "csv"],
                    with_data=True,
                ),
                timeout=60,
            )
        except asyncio.TimeoutError:
            self._mostrar_snack(
                "El selector de archivos tardó demasiado. Intente de nuevo.",
                error=True,
            )
            return
        except Exception as ex:
            self._mostrar_snack(
                f"No se pudo abrir el selector de archivos: {ex}", error=True
            )
            return
        finally:
            try:
                self.page.services.remove(file_picker)
            except Exception:
                pass

        if not archivos:
            return

        archivo = archivos[0]

        if archivo.path:
            self._import_ruta.value = archivo.path
        elif archivo.bytes:
            extension = (
                archivo.name.split(".")[-1].lower()
                if "." in archivo.name
                else "xlsx"
            )
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=f".{extension}"
                ) as tmp:
                    tmp.write(archivo.bytes)
                    self._import_ruta.value = tmp.name
            except Exception as ex:
                self._mostrar_snack(
                    f"No se pudo guardar el archivo temporal: {ex}", error=True
                )
                return
        else:
            self._mostrar_snack(
                "No se obtuvo la ruta ni el contenido del archivo.", error=True
            )
            return

        self.page.update()

    def _importar_excel(self, e=None):
        bodega_id = self._import_bodega.value
        ruta = (self._import_ruta.value or "").strip()

        if not bodega_id:
            self._mostrar_snack("⚠️ Selecciona una bodega destino.", error=True)
            return
        if not ruta:
            self._mostrar_snack("⚠️ Selecciona un archivo para importar.", error=True)
            return

        self._cerrar_dialogo_importar()

        def _worker():
            result = ProductosService.importar_excel(
                ruta_archivo=ruta, bodega_id=bodega_id
            )
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
