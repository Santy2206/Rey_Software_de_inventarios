"""
Vista de Ventas.

Permite registrar una venta (cliente + productos), descontar stock
automáticamente y consultar el historial. Sigue el mismo patrón que
productos_view.py / movimientos_view.py:
  - Función pública VentasView() que envuelve la clase privada.
  - Clase _VentasView hereda de ft.Container.
  - Carga de datos y escrituras corren en hilos de fondo (threading).
  - Dialog y SnackBar se registran en page.overlay desde did_mount().

Reglas:
    - SIN lógica de negocio — solo diseño e interacción de interfaz.
    - SIN llamadas directas a la base de datos.
    - SIN ft.app() — esta vista es montada por dashboard_view.py.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import flet as ft

from src.services.auth_service import AuthService
from src.services.bodegas_service import BodegasService
from src.services.clientes_service import ClientesService
from src.services.productos_service import ProductosService
from src.services.usuarios_service import UsuariosService
from src.services.ventas_import_service import VentasImportService
from src.services.ventas_service import VentasService
from src.ui.components.status_header import StatusHeader
from src.ui.components.page_header import PageHeader


def VentasView():
    return ft.Column(controls=[_VentasView()])


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _fmt_money(value) -> str:
    return f"${_money(value):,.2f}"


class _VentasView(ft.Container):

    def __init__(self):
        super().__init__()
        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        self._clientes: list[dict] = []
        self._productos: list[dict] = []
        self._ventas: list[dict] = []
        self._carrito: list[dict] = []
        self._bodegas: list[dict] = []
        self._usuarios: list[dict] = []

        self._campo_cliente = ft.Dropdown(
            label="Cliente *",
            expand=True,
            border_radius=10,
            options=[],
        )
        self._campo_producto = ft.Dropdown(
            label="Producto *",
            expand=True,
            border_radius=10,
            options=[],
            on_select=self._al_elegir_producto,
        )
        self._campo_cantidad = ft.TextField(
            label="Cantidad *",
            value="1",
            expand=True,
            border_radius=10,
        )
        self._campo_precio = ft.TextField(
            label="Precio unitario",
            value="$0.00",
            read_only=True,
            expand=True,
            border_radius=10,
        )
        self._lbl_total = ft.Text(
            "$0.00",
            size=28,
            weight=ft.FontWeight.BOLD,
            color="#b3001b",
        )
        self._lista_carrito = ft.Column(
            spacing=0,
            controls=[
                ft.Text("El carrito está vacío.", color="grey", italic=True)
            ],
        )
        self._tabla = ft.DataTable(
            expand=True,
            border=ft.Border.all(1, "#eeeeee"),
            border_radius=10,
            vertical_lines=ft.BorderSide(1, "#eeeeee"),
            horizontal_lines=ft.BorderSide(1, "#eeeeee"),
            heading_row_color="#fafafa",
            columns=[
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Cliente")),
                ft.DataColumn(ft.Text("Items")),
                ft.DataColumn(ft.Text("Total")),
                ft.DataColumn(ft.Text("Usuario")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=[],
        )
        self._lbl_registros = ft.Text(
            "0 registros",
            color="#4338CA",
            weight=ft.FontWeight.BOLD,
        )
        self._buscar = ft.TextField(
            width=300,
            hint_text="Buscar cliente...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._aplicar_filtros,
        )
        self._picker_inicio = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2100, 12, 31),
            on_change=self._on_fecha_inicio,
        )
        self._picker_fin = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2100, 12, 31),
            on_change=self._on_fecha_fin,
        )
        self._filtro_fecha_inicio = ft.TextField(
            label="Fecha inicio",
            hint_text="dd/mm/aaaa",
            width=130,
            on_change=self._on_change_fecha_inicio,
            on_blur=self._aplicar_filtros,
            on_submit=self._aplicar_filtros,
        )
        self._btn_calendario_inicio = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH,
            tooltip="Seleccionar fecha inicio",
            on_click=lambda _: self._abrir_calendario("inicio"),
        )
        self._filtro_fecha_fin = ft.TextField(
            label="Fecha fin",
            hint_text="dd/mm/aaaa",
            width=130,
            on_change=self._on_change_fecha_fin,
            on_blur=self._aplicar_filtros,
            on_submit=self._aplicar_filtros,
        )
        self._btn_calendario_fin = ft.IconButton(
            icon=ft.Icons.CALENDAR_MONTH,
            tooltip="Seleccionar fecha fin",
            on_click=lambda _: self._abrir_calendario("fin"),
        )
        self._filtro_bodega = ft.Dropdown(
            label="Bodega",
            width=200,
            options=[ft.DropdownOption(key="", text="Todas")],
            value="",
            on_select=self._aplicar_filtros,
        )
        self._filtro_usuario = ft.Dropdown(
            label="Vendedor",
            width=200,
            options=[ft.DropdownOption(key="", text="Todos")],
            value="",
            on_select=self._aplicar_filtros,
        )

        self._campo_cedula_cliente = ft.TextField(
            label="Cédula *",
            hint_text="Ej: 12345678",
            border_radius=10,
        )
        self._campo_nombre_cliente = ft.TextField(
            label="Nombre *",
            hint_text="Ej: Juan Pérez",
            border_radius=10,
        )
        self._campo_telefono_cliente = ft.TextField(
            label="Teléfono",
            hint_text="Ej: 3001234567",
            border_radius=10,
        )
        self._campo_email_cliente = ft.TextField(
            label="Email",
            hint_text="Ej: correo@ejemplo.com",
            border_radius=10,
        )
        self._dialog_cliente = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo cliente"),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    self._campo_cedula_cliente,
                    self._campo_nombre_cliente,
                    self._campo_telefono_cliente,
                    self._campo_email_cliente,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_cliente),
                ft.ElevatedButton(
                    "Guardar",
                    bgcolor="#b3001b",
                    color="white",
                    on_click=self._guardar_cliente,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._venta_a_anular = None
        self._dialog_anular = ft.AlertDialog(
            modal=True,
            title=ft.Text("Anular venta"),
            content=ft.Text(
                "¿Anular esta venta? El stock de los productos "
                "vendidos será devuelto al inventario."
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_anular),
                ft.ElevatedButton(
                    "Anular",
                    bgcolor="#b3001b",
                    color="white",
                    on_click=self._confirmar_anulacion,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._import_ruta = ft.TextField(
            label="Ruta del archivo",
            hint_text="C:\\Users\\...\\ventas_elisa.xls",
            border_radius=10,
            expand=True,
        )
        self._dialog_importar = ft.AlertDialog(
            modal=True,
            title=ft.Text("Importar ventas desde Elisa (.xls/.xlsx)"),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    ft.Text(
                        "El archivo se aterriza en la cola de revisión; "
                        "no se crean ventas ni se descuenta stock aquí.",
                        size=12,
                        color="grey",
                    ),
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
                    bgcolor="#b3001b",
                    color="white",
                    on_click=self._importar_ventas,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._tabla_detalle = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Producto")),
                ft.DataColumn(ft.Text("Cantidad")),
                ft.DataColumn(ft.Text("Precio unitario")),
                ft.DataColumn(ft.Text("Subtotal")),
            ],
            rows=[],
            expand=True,
        )
        self._lbl_detalle_header = ft.Text("", size=14, color="grey")
        self._dialog_detalle = ft.AlertDialog(
            modal=True,
            title=ft.Text("Detalle de venta"),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    self._lbl_detalle_header,
                    self._tabla_detalle,
                ],
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=self._cerrar_dialogo_detalle),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._snackbar = ft.SnackBar(content=ft.Text(""), show_close_icon=True)

        self._status_header = StatusHeader()

        self.content = ft.Column(
            spacing=0,
            expand=True,
            controls=[
                self._header(),
                ft.Container(height=20),
                self._formulario(),
                ft.Container(height=20),
                self._historial(),
            ],
        )

    def did_mount(self):
        self.page.overlay.append(self._dialog_cliente)
        self.page.overlay.append(self._dialog_anular)
        self.page.overlay.append(self._dialog_importar)
        self.page.overlay.append(self._dialog_detalle)
        self.page.overlay.append(self._picker_inicio)
        self.page.overlay.append(self._picker_fin)
        self.page.overlay.append(self._snackbar)
        self.page.update()
        self._status_header.load(self.page)
        threading.Thread(target=self._cargar_datos_iniciales, daemon=True).start()

    def _cargar_datos_iniciales(self):
        res_clientes = ClientesService.get_all()
        self._clientes = res_clientes["data"] if res_clientes.get("success") else []
        self._refrescar_dropdown_clientes()

        res_productos = ProductosService.get_all()
        self._productos = res_productos["data"] if res_productos.get("success") else []
        self._refrescar_dropdown_productos()

        res_bodegas = BodegasService.get_all()
        self._bodegas = res_bodegas["data"] if res_bodegas.get("success") else []
        self._refrescar_filtro_bodegas()

        res_usuarios = UsuariosService.get_all()
        self._usuarios = res_usuarios["data"] if res_usuarios.get("success") else []
        self._refrescar_filtro_usuarios()

        self._cargar_historial()
        self.page.update()

    def _cargar_historial(self):
        inicio = self._fecha_a_iso(
            (self._filtro_fecha_inicio.value or "").strip()
        )
        fin = self._fecha_a_iso(
            (self._filtro_fecha_fin.value or "").strip()
        )

        if inicio and fin and inicio > fin:
            self._mostrar_snack(
                "La fecha fin debe ser mayor o igual a la fecha inicio",
                error=True,
            )
            self._ventas = []
            self._refrescar_tabla()
            return

        bodega = (self._filtro_bodega.value or "").strip() or None
        usuario = (self._filtro_usuario.value or "").strip() or None
        cliente = (self._buscar.value or "").strip() or None

        resultado = VentasService.get_all(
            cliente=cliente,
            fecha_inicio=inicio,
            fecha_fin=fin,
            bodega_id=bodega,
            usuario_id=usuario,
        )
        self._ventas = resultado["data"] if resultado.get("success") else []
        self._refrescar_tabla()

    def _refrescar_dropdown_clientes(self, seleccionar_id: str = None):
        self._campo_cliente.options = [
            ft.DropdownOption(key=str(c["id"]), text=c.get("nombre", "—"))
            for c in self._clientes
        ]
        if seleccionar_id:
            self._campo_cliente.value = str(seleccionar_id)

    def _refrescar_dropdown_productos(self):
        self._campo_producto.options = [
            ft.DropdownOption(
                key=str(p["id"]),
                text=f"{p.get('nombre', '—')} — stock {p.get('stock_actual', 0)}",
            )
            for p in self._productos
        ]

    def _refrescar_filtro_bodegas(self):
        opciones = [ft.DropdownOption(key="", text="Todas")]
        opciones.extend(
            [
                ft.DropdownOption(key=str(b["id"]), text=b.get("nombre", "—"))
                for b in self._bodegas
            ]
        )
        self._filtro_bodega.options = opciones

    def _refrescar_filtro_usuarios(self):
        opciones = [ft.DropdownOption(key="", text="Todos")]
        opciones.extend(
            [
                ft.DropdownOption(key=str(u["id"]), text=u.get("name", "—"))
                for u in self._usuarios
            ]
        )
        self._filtro_usuario.options = opciones

    def _header(self):
        return PageHeader(
            title="Ventas",
            subtitle="Registro de ventas con descuento automático de stock",
            status_control=self._status_header.control,
            action_buttons=[
                ft.ElevatedButton(
                    "Importar ventas",
                    icon=ft.Icons.UPLOAD_FILE,
                    bgcolor="#b3001b",
                    color="white",
                    height=45,
                    on_click=self._abrir_dialogo_importar,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10)
                    ),
                ),
            ],
        )

    def _formulario(self):
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
                spacing=16,
                controls=[
                    ft.Text(
                        "Nueva venta",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            self._campo_cliente,
                            ft.ElevatedButton(
                                "Nuevo cliente",
                                icon=ft.Icons.PERSON_ADD,
                                bgcolor="#b3001b",
                                color="white",
                                height=50,
                                on_click=self._abrir_dialogo_cliente,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            self._campo_producto,
                            self._campo_cantidad,
                            self._campo_precio,
                            ft.ElevatedButton(
                                "Agregar",
                                icon=ft.Icons.ADD_SHOPPING_CART,
                                bgcolor="#16A34A",
                                color="white",
                                height=50,
                                on_click=self._agregar_al_carrito,
                            ),
                        ],
                    ),
                    ft.Divider(),
                    ft.Text("Carrito", weight=ft.FontWeight.BOLD, size=16),
                    self._lista_carrito,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Total", size=16, color="grey"),
                            self._lbl_total,
                        ],
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        spacing=10,
                        controls=[
                            ft.OutlinedButton(
                                "CANCELAR",
                                height=50,
                                on_click=self._limpiar_venta,
                            ),
                            ft.FilledButton(
                                "REGISTRAR VENTA",
                                icon=ft.Icons.POINT_OF_SALE,
                                height=50,
                                style=ft.ButtonStyle(
                                    bgcolor="#b3001b",
                                    color="white",
                                ),
                                on_click=self._registrar_venta,
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _historial(self):
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
                spacing=16,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(
                                        "Historial de ventas",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        "Consulta las ventas registradas",
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
                        wrap=True,
                        spacing=10,
                        run_spacing=10,
                        alignment=ft.MainAxisAlignment.START,
                        controls=[
                            self._buscar,
                            ft.Row(
                                spacing=0,
                                controls=[
                                    self._filtro_fecha_inicio,
                                    self._btn_calendario_inicio,
                                ],
                            ),
                            ft.Row(
                                spacing=0,
                                controls=[
                                    self._filtro_fecha_fin,
                                    self._btn_calendario_fin,
                                ],
                            ),
                            self._filtro_bodega,
                            self._filtro_usuario,
                        ],
                    ),
                    ft.Divider(),
                    self._tabla,
                ],
            ),
        )

    def _al_elegir_producto(self, e=None):
        producto = self._buscar_producto(self._campo_producto.value)
        if producto:
            self._campo_precio.value = _fmt_money(producto.get("precio"))
        else:
            self._campo_precio.value = "$0.00"
        self.update()

    def _buscar_producto(self, producto_id: str):
        if not producto_id:
            return None
        for producto in self._productos:
            if str(producto["id"]) == str(producto_id):
                return producto
        return None

    def _fecha_a_iso(self, fecha_str: str) -> str | None:
        """Convierte dd/mm/aaaa a aaaa-mm-dd para el filtro de ventas."""
        if not fecha_str:
            return None
        try:
            return datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _on_fecha_inicio(self, e):
        fecha = e.control.value
        self._filtro_fecha_inicio.value = (
            fecha.strftime("%d/%m/%Y") if fecha else ""
        )
        self.update()
        self._aplicar_filtros()

    def _on_fecha_fin(self, e):
        fecha = e.control.value
        self._filtro_fecha_fin.value = (
            fecha.strftime("%d/%m/%Y") if fecha else ""
        )
        self.update()
        self._aplicar_filtros()

    def _formatear_fecha(self, texto: str) -> str:
        """Convierte digitos sueltos a dd/mm/aaaa mientras se escribe."""
        digitos = "".join(c for c in (texto or "") if c.isdigit())[:8]
        if len(digitos) >= 7:
            return f"{digitos[:2]}/{digitos[2:4]}/{digitos[4:]}"
        if len(digitos) >= 5:
            return f"{digitos[:2]}/{digitos[2:4]}/{digitos[4:]}"
        if len(digitos) >= 3:
            return f"{digitos[:2]}/{digitos[2:]}"
        return digitos

    def _on_change_fecha_inicio(self, e):
        self._filtro_fecha_inicio.value = self._formatear_fecha(
            e.control.value
        )
        self._filtro_fecha_inicio.update()
        if len(self._filtro_fecha_inicio.value) in (0, 10):
            self._aplicar_filtros()

    def _on_change_fecha_fin(self, e):
        self._filtro_fecha_fin.value = self._formatear_fecha(
            e.control.value
        )
        self._filtro_fecha_fin.update()
        if len(self._filtro_fecha_fin.value) in (0, 10):
            self._aplicar_filtros()

    def _abrir_calendario(self, tipo: str):
        picker = (
            self._picker_inicio if tipo == "inicio" else self._picker_fin
        )
        picker.open = True
        self.page.update()

    def _agregar_al_carrito(self, e=None):
        producto_id = self._campo_producto.value
        producto = self._buscar_producto(producto_id)
        if not producto:
            self._mostrar_snack("⚠️ Selecciona un producto.", error=True)
            return

        try:
            cantidad = int((self._campo_cantidad.value or "").strip())
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            self._mostrar_snack(
                "⚠️ La cantidad debe ser un número entero mayor a 0.", error=True
            )
            return

        stock = int(producto.get("stock_actual") or 0)
        ya_en_carrito = sum(
            item["cantidad"]
            for item in self._carrito
            if item["producto_id"] == str(producto["id"])
        )
        if ya_en_carrito + cantidad > stock:
            self._mostrar_snack(
                f"⚠️ Stock insuficiente de '{producto.get('nombre')}'. "
                f"Disponible: {stock}.",
                error=True,
            )
            return

        precio = _money(producto.get("precio"))
        existente = next(
            (
                item
                for item in self._carrito
                if item["producto_id"] == str(producto["id"])
            ),
            None,
        )
        if existente:
            existente["cantidad"] += cantidad
            existente["subtotal"] = _money(existente["precio"] * existente["cantidad"])
        else:
            self._carrito.append(
                {
                    "producto_id": str(producto["id"]),
                    "nombre": producto.get("nombre", "—"),
                    "cantidad": cantidad,
                    "precio": precio,
                    "subtotal": _money(precio * cantidad),
                }
            )

        self._campo_cantidad.value = "1"
        self._refrescar_carrito()
        self.update()

    def _quitar_del_carrito(self, producto_id: str):
        self._carrito = [
            item for item in self._carrito if item["producto_id"] != producto_id
        ]
        self._refrescar_carrito()
        self.update()

    def _refrescar_carrito(self):
        self._lista_carrito.controls.clear()
        if not self._carrito:
            self._lista_carrito.controls.append(
                ft.Text("El carrito está vacío.", color="grey", italic=True)
            )
            self._lbl_total.value = "$0.00"
            return

        total = Decimal("0.00")
        for item in self._carrito:
            total += item["subtotal"]
            producto_id = item["producto_id"]
            self._lista_carrito.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.SHOPPING_BAG, color="#b3001b"),
                    title=ft.Text(item["nombre"]),
                    subtitle=ft.Text(
                        f"{item['cantidad']} x {_fmt_money(item['precio'])} = {_fmt_money(item['subtotal'])}"
                    ),
                    trailing=ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color="red",
                        tooltip="Quitar",
                        on_click=lambda e, pid=producto_id: self._quitar_del_carrito(
                            pid
                        ),
                    ),
                )
            )
        self._lbl_total.value = _fmt_money(total)

    def _registrar_venta(self, e=None):
        cliente_id = self._campo_cliente.value
        if not cliente_id:
            self._mostrar_snack("⚠️ Selecciona un cliente.", error=True)
            return
        if not self._carrito:
            self._mostrar_snack("⚠️ Agrega al menos un producto al carrito.", error=True)
            return

        items = [
            {"producto_id": item["producto_id"], "cantidad": item["cantidad"]}
            for item in self._carrito
        ]
        usuario_id = AuthService.get_usuario_id()

        def _worker():
            result = VentasService.registrar(
                cliente_id=cliente_id,
                items=items,
                usuario_id=usuario_id,
            )
            self._mostrar_snack(result["message"], error=not result["success"])
            if result["success"]:
                self._limpiar_venta()
                self._cargar_datos_iniciales()

        threading.Thread(target=_worker, daemon=True).start()

    def _limpiar_venta(self, e=None):
        self._carrito = []
        self._campo_producto.value = None
        self._campo_cantidad.value = "1"
        self._campo_precio.value = "$0.00"
        self._refrescar_carrito()
        if self.page:
            self.page.update()

    def _abrir_dialogo_cliente(self, e=None):
        self._campo_cedula_cliente.value = ""
        self._campo_nombre_cliente.value = ""
        self._campo_telefono_cliente.value = ""
        self._campo_email_cliente.value = ""
        self._dialog_cliente.open = True
        self.page.update()

    def _cerrar_dialogo_cliente(self, e=None):
        self._dialog_cliente.open = False
        self.page.update()

    def _guardar_cliente(self, e=None):
        cedula = (self._campo_cedula_cliente.value or "").strip()
        nombre = (self._campo_nombre_cliente.value or "").strip()
        if not cedula:
            self._mostrar_snack("⚠️ La cédula del cliente es obligatoria.", error=True)
            return
        if not nombre:
            self._mostrar_snack("⚠️ El nombre del cliente es obligatorio.", error=True)
            return

        telefono = (self._campo_telefono_cliente.value or "").strip()
        email = (self._campo_email_cliente.value or "").strip()
        self._cerrar_dialogo_cliente()

        def _worker():
            result = ClientesService.create(
                cedula=cedula, nombre=nombre, telefono=telefono, email=email
            )
            self._mostrar_snack(result["message"], error=not result["success"])
            if result["success"]:
                nuevo = result["data"]
                self._clientes.append(nuevo)
                self._clientes.sort(key=lambda c: (c.get("nombre") or "").lower())
                self._refrescar_dropdown_clientes(seleccionar_id=str(nuevo["id"]))
                self.page.update()

        threading.Thread(target=_worker, daemon=True).start()

    def _refrescar_tabla(self):
        self._tabla.rows = [self._crear_fila(v) for v in self._ventas]
        self._lbl_registros.value = f"{len(self._tabla.rows)} registros"

    def _crear_fila(self, venta: dict):
        fecha = venta.get("fecha")
        fecha_str = (
            fecha.strftime("%d/%m/%Y %H:%M")
            if hasattr(fecha, "strftime")
            else str(fecha or "—")
        )
        anulada = bool(venta.get("anulada"))
        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(fecha_str)),
                ft.DataCell(ft.Text(venta.get("cliente_nombre") or "—")),
                ft.DataCell(ft.Text(str(venta.get("unidades") or 0))),
                ft.DataCell(
                    ft.Text(
                        _fmt_money(venta.get("total")),
                        weight=ft.FontWeight.BOLD,
                    )
                ),
                ft.DataCell(ft.Text(venta.get("usuario_nombre") or "—")),
                ft.DataCell(
                    ft.Container(
                        bgcolor="#FEE2E2" if anulada else "#DCFCE7",
                        border_radius=20,
                        padding=6,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            "Anulada" if anulada else "Completada",
                            color="#B91C1C" if anulada else "#15803D",
                            weight=ft.FontWeight.BOLD,
                            size=11,
                        ),
                    )
                ),
                ft.DataCell(
                    ft.Row(
                        spacing=0,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.VISIBILITY,
                                icon_color="#4338CA",
                                tooltip="Ver detalle",
                                on_click=lambda e, v=venta: self._abrir_dialogo_detalle(
                                    v
                                ),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CANCEL,
                                icon_color="#B91C1C",
                                tooltip="Anular venta",
                                disabled=anulada,
                                on_click=lambda e, v=venta: self._abrir_dialogo_anular(
                                    v
                                ),
                            ),
                        ],
                    )
                ),
            ]
        )

    def _abrir_dialogo_anular(self, venta: dict):
        self._venta_a_anular = venta
        self._dialog_anular.open = True
        self.page.update()

    def _cerrar_dialogo_anular(self, e=None):
        self._venta_a_anular = None
        self._dialog_anular.open = False
        self.page.update()

    def _abrir_dialogo_detalle(self, venta: dict):
        def _worker():
            result = VentasService.get_by_id(str(venta["id"]))
            if not result.get("success"):
                self._mostrar_snack(result["message"], error=True)
                return
            data = result["data"]
            fecha = data.get("fecha")
            fecha_str = (
                fecha.strftime("%d/%m/%Y %H:%M")
                if hasattr(fecha, "strftime")
                else str(fecha or "—")
            )
            header = (
                f"{fecha_str} · Cliente: {data.get('cliente_nombre') or '—'} "
                f"· Total: {_fmt_money(data.get('total'))} "
                f"· Vendedor: {data.get('usuario_nombre') or '—'}"
            )
            self._lbl_detalle_header.value = header

            self._tabla_detalle.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(linea.get("producto_nombre") or "—")),
                        ft.DataCell(
                            ft.Text(str(linea.get("cantidad") or 0))
                        ),
                        ft.DataCell(
                            ft.Text(_fmt_money(linea.get("precio_unitario")))
                        ),
                        ft.DataCell(
                            ft.Text(_fmt_money(linea.get("subtotal")))
                        ),
                    ]
                )
                for linea in data.get("lineas", [])
            ]
            self._dialog_detalle.open = True
            if self.page:
                self.page.update()

        threading.Thread(target=_worker, daemon=True).start()

    def _cerrar_dialogo_detalle(self, e=None):
        self._dialog_detalle.open = False
        if self.page:
            self.page.update()

    def _confirmar_anulacion(self, e=None):
        venta = self._venta_a_anular
        self._cerrar_dialogo_anular()
        if not venta:
            return

        usuario_id = AuthService.get_usuario_id()

        def _worker():
            result = VentasService.anular(
                venta_id=str(venta["id"]),
                usuario_id=usuario_id,
            )
            self._mostrar_snack(result["message"], error=not result["success"])
            if result["success"]:
                self._cargar_historial()
                self.page.update()

        threading.Thread(target=_worker, daemon=True).start()


    def _aplicar_filtros(self, e=None):
        def _worker():
            self._cargar_historial()
            if self.page:
                self.page.update()

        threading.Thread(target=_worker, daemon=True).start()

    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        if self.page:
            self.page.update()

    # ---------------- Importación Elisa ----------------
    def _abrir_dialogo_importar(self, e=None):
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
                    "$f.Filter = 'Excel Elisa (*.xls,*.xlsx)|*.xls;*.xlsx|"
                    "Todos los archivos (*.*)|*.*'; "
                    "$f.Title = 'Seleccionar archivo de ventas Elisa'; "
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
        """FilePicker en modo web (debe registrarse en page.services)."""
        file_picker = ft.FilePicker()
        self.page.services.append(file_picker)
        self.page.update()
        try:
            archivos = await asyncio.wait_for(
                file_picker.pick_files(
                    dialog_title="Seleccionar archivo de ventas Elisa",
                    allow_multiple=False,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["xls", "xlsx"],
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
                else "xls"
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

    def _importar_ventas(self, e=None):
        ruta = (self._import_ruta.value or "").strip()
        if not ruta:
            self._mostrar_snack(
                "Seleccione el archivo de ventas Elisa.", error=True
            )
            return
        if not os.path.exists(ruta):
            self._mostrar_snack(
                "El archivo no existe en la ruta indicada.", error=True
            )
            return

        self._dialog_importar.open = False
        self.page.update()

        def _worker():
            res = VentasImportService.importar_raw(ruta)
            self._mostrar_snack(
                res.get("message", "Importación finalizada"),
                error=not res.get("success"),
            )

        threading.Thread(target=_worker, daemon=True).start()
