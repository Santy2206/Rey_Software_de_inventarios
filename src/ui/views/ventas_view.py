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

import threading
from decimal import Decimal, ROUND_HALF_UP

import flet as ft

from src.services.auth_service import AuthService
from src.services.clientes_service import ClientesService
from src.services.productos_service import ProductosService
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
            ],
            rows=[],
        )
        self._lbl_registros = ft.Text(
            "0 registros",
            color="#4338CA",
            weight=ft.FontWeight.BOLD,
        )
        self._buscar = ft.TextField(
            expand=True,
            hint_text="Buscar por cliente...",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._aplicar_filtros,
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

        self._cargar_historial()
        self.page.update()

    def _cargar_historial(self):
        resultado = VentasService.get_all()
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
                    self._buscar,
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
        self._campo_nombre_cliente.value = ""
        self._campo_telefono_cliente.value = ""
        self._campo_email_cliente.value = ""
        self._dialog_cliente.open = True
        self.page.update()

    def _cerrar_dialogo_cliente(self, e=None):
        self._dialog_cliente.open = False
        self.page.update()

    def _guardar_cliente(self, e=None):
        nombre = (self._campo_nombre_cliente.value or "").strip()
        if not nombre:
            self._mostrar_snack("⚠️ El nombre del cliente es obligatorio.", error=True)
            return

        telefono = (self._campo_telefono_cliente.value or "").strip()
        email = (self._campo_email_cliente.value or "").strip()
        self._cerrar_dialogo_cliente()

        def _worker():
            result = ClientesService.create(
                nombre=nombre, telefono=telefono, email=email
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
            ]
        )

    def _aplicar_filtros(self, e=None):
        texto = (self._buscar.value or "").lower()
        for fila in self._tabla.rows:
            cliente = (fila.cells[1].content.value or "").lower()
            fila.visible = texto in cliente
        self.update()

    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        if self.page:
            self.page.update()
