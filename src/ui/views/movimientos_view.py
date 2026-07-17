import flet as ft
from datetime import datetime


class MovimientosView(ft.Container):

    def __init__(self):
        super().__init__()

        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

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
                ft.Tab(
                    text="Entrada",
                    icon=ft.Icons.DOWNLOAD,
                ),
                ft.Tab(
                    text="Salida",
                    icon=ft.Icons.UPLOAD,
                ),
                ft.Tab(
                    text="Baja",
                    icon=ft.Icons.DELETE,
                ),
            ],
        )

        self.bodega = ft.Dropdown(
            label="Bodega *",
            expand=True,
            options=[
                ft.dropdown.Option("Fragancias"),
                ft.dropdown.Option("General"),
                ft.dropdown.Option("Rola Negra"),
            ],
        )

        self.producto = ft.Dropdown(
            label="Producto *",
            expand=True,
            options=[
                ft.dropdown.Option("Producto 1"),
                ft.dropdown.Option("Producto 2"),
                ft.dropdown.Option("Producto 3"),
            ],
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


def actualizar_contador(self):
    self.lbl_registros.value = f"{len(self.tabla.rows)} registros"
    self.update()

    # ============================================================
    # HISTORIAL
    # ============================================================


def history_section(self):
    self.filtro_tipo = ft.Dropdown(
        width=180,
        label="Tipo",
        value="Todos",
        options=[
            ft.dropdown.Option("Todos"),
            ft.dropdown.Option("Entrada"),
            ft.dropdown.Option("Salida"),
            ft.dropdown.Option("Baja"),
        ],
    )

    self.filtro_bodega = ft.Dropdown(
        width=200,
        label="Bodega",
        value="Todas",
        options=[
            ft.dropdown.Option("Todas"),
            ft.dropdown.Option("Fragancias"),
            ft.dropdown.Option("General"),
            ft.dropdown.Option("Rola Negra"),
        ],
    )

    self.buscar = ft.TextField(
        on_change=self.buscar_producto,
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
        rows=[
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text("24/03/2026")),
                    ft.DataCell(
                        ft.Container(
                            bgcolor="#DCFCE7",
                            border_radius=20,
                            padding=6,
                            content=ft.Text(
                                "Entrada",
                                color="#15803D",
                                weight=ft.FontWeight.BOLD,
                            ),
                        )
                    ),
                    ft.DataCell(ft.Text("General")),
                    ft.DataCell(ft.Text("Perfume Rey")),
                    ft.DataCell(ft.Text("120")),
                    ft.DataCell(ft.Text("admin")),
                ]
            ),
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text("24/03/2026")),
                    ft.DataCell(
                        ft.Container(
                            bgcolor="#FEE2E2",
                            border_radius=20,
                            padding=6,
                            content=ft.Text(
                                "Salida",
                                color="#B91C1C",
                                weight=ft.FontWeight.BOLD,
                            ),
                        )
                    ),
                    ft.DataCell(ft.Text("Fragancias")),
                    ft.DataCell(ft.Text("Splash")),
                    ft.DataCell(ft.Text("15")),
                    ft.DataCell(ft.Text("admin")),
                ]
            ),
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text("24/03/2026")),
                    ft.DataCell(
                        ft.Container(
                            bgcolor="#FEF3C7",
                            border_radius=20,
                            padding=6,
                            content=ft.Text(
                                "Baja",
                                color="#B45309",
                                weight=ft.FontWeight.BOLD,
                            ),
                        )
                    ),
                    ft.DataCell(ft.Text("Rola Negra")),
                    ft.DataCell(ft.Text("Crema")),
                    ft.DataCell(ft.Text("3")),
                    ft.DataCell(ft.Text("admin")),
                ]
            ),
        ],
    )

    # ✅ Asignación fuera del bloque visual
    self.lbl_registros = ft.Text(
        f"{len(self.tabla.rows)} registros",
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
                                        ft.Icons.LIST_ALT,
                                        color="#4338CA",
                                        size=16,
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

    # ============================================================
    # CAMBIO DE TIPO DE MOVIMIENTO
    # ============================================================

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

        if self.bodega.value is None:
            return

        if self.producto.value is None:
            return

        if self.cantidad.value == "":
            return

        tipo = "Entrada"

        color = "#DCFCE7"
        texto = "#15803D"

        if self.tipo.selected_index == 1:
            tipo = "Salida"
            color = "#FEE2E2"
            texto = "#B91C1C"

        if self.tipo.selected_index == 2:
            tipo = "Baja"
            color = "#FEF3C7"
            texto = "#B45309"

        fila = ft.DataRow(
            cells=[
                ft.DataCell(
                    ft.Text(
                        self.fecha.value,
                    )
                ),
                ft.DataCell(
                    ft.Container(
                        bgcolor=color,
                        border_radius=20,
                        padding=6,
                        content=ft.Text(
                            tipo,
                            color=texto,
                            weight=ft.FontWeight.BOLD,
                        ),
                    )
                ),
                ft.DataCell(ft.Text(self.bodega.value)),
                ft.DataCell(ft.Text(self.producto.value)),
                ft.DataCell(ft.Text(self.cantidad.value)),
                ft.DataCell(ft.Text("admin")),
            ]
        )

        self.tabla.rows.insert(0, fila)
        self.actualizar_contador()
        self.limpiar_formulario()

    # ============================================================
    # BOTÓN
    # ============================================================

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
        # ============================================================

    # LIMPIAR FORMULARIO
    # ============================================================

    def limpiar_formulario(self):

        self.bodega.value = None
        self.producto.value = None
        self.cantidad.value = ""
        self.notas.value = ""

        self.update()
        # ============================================================

    # BUSCAR
    # ============================================================

    def buscar_producto(self, e):

        texto = self.buscar.value.lower()

        for fila in self.tabla.rows:

            producto = fila.cells[3].content.value.lower()

            fila.visible = texto in producto

        self.update()
