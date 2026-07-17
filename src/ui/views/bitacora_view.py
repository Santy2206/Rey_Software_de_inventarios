import flet as ft


class BitacoraView(ft.Container):

    def __init__(self):
        super().__init__()

        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                self.header_section(),
                ft.Container(height=20),
                self.tabla_section(),
            ],
        )

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
            on_change=self.buscar_usuario,
        )

        self.filtro = ft.Dropdown(
            on_change=self.filtrar_accion,
            width=180,
            label="Acción",
            value="Todas",
            options=[
                ft.dropdown.Option("Todas"),
                ft.dropdown.Option("LOGIN"),
                ft.dropdown.Option("ENTRADA"),
                ft.dropdown.Option("SALIDA"),
                ft.dropdown.Option("BAJA"),
                ft.dropdown.Option("PRODUCTO"),
                ft.dropdown.Option("BODEGA"),
            ],
        )

        self.total = ft.Text(
            "8 registros",
            color="#4338CA",
            weight=ft.FontWeight.BOLD,
        )

        self.tabla = ft.DataTable(
            expand=True,
            border=ft.border.all(1, "#eeeeee"),
            border_radius=10,
            vertical_lines=ft.BorderSide(
                1,
                "#eeeeee",
            ),
            horizontal_lines=ft.BorderSide(
                1,
                "#eeeeee",
            ),
            heading_row_color="#fafafa",
            columns=[
                ft.DataColumn(ft.Text("Fecha / Hora")),
                ft.DataColumn(ft.Text("Usuario")),
                ft.DataColumn(ft.Text("Rol")),
                ft.DataColumn(ft.Text("Acción")),
                ft.DataColumn(ft.Text("Detalle")),
            ],
            rows=[
                self.crear_fila(
                    "24/03/2026 08:10",
                    "admin",
                    "Administrador",
                    "LOGIN",
                    "Inicio de sesión",
                ),
                self.crear_fila(
                    "24/03/2026 08:20",
                    "admin",
                    "Administrador",
                    "ENTRADA",
                    "Ingresó 120 unidades de Perfume Rey",
                ),
                self.crear_fila(
                    "24/03/2026 09:15",
                    "admin",
                    "Administrador",
                    "SALIDA",
                    "Salida de 15 unidades",
                ),
                self.crear_fila(
                    "24/03/2026 09:45",
                    "admin",
                    "Administrador",
                    "BAJA",
                    "Producto vencido",
                ),
                self.crear_fila(
                    "24/03/2026 10:00",
                    "admin",
                    "Administrador",
                    "PRODUCTO",
                    "Creó nuevo producto",
                ),
                self.crear_fila(
                    "24/03/2026 10:30",
                    "admin",
                    "Administrador",
                    "BODEGA",
                    "Creó bodega Fragancias",
                ),
            ],
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

    # CREAR FILA
    # ======================================================

    def crear_fila(self, fecha, usuario, rol, accion, detalle):

        colores = {
            "LOGIN": ("#DBEAFE", "#1D4ED8"),
            "ENTRADA": ("#DCFCE7", "#15803D"),
            "SALIDA": ("#FEE2E2", "#B91C1C"),
            "BAJA": ("#FEF3C7", "#B45309"),
            "PRODUCTO": ("#EDE9FE", "#6D28D9"),
            "BODEGA": ("#FCE7F3", "#BE185D"),
        }

        fondo, texto = colores.get(accion, ("#F3F4F6", "#374151"))

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(fecha)),
                ft.DataCell(ft.Text(usuario)),
                ft.DataCell(ft.Text(rol)),
                ft.DataCell(
                    ft.Container(
                        bgcolor=fondo,
                        border_radius=20,
                        padding=6,
                        alignment=ft.alignment.center,
                        content=ft.Text(
                            accion,
                            color=texto,
                            weight=ft.FontWeight.BOLD,
                            size=11,
                        ),
                    )
                ),
                ft.DataCell(ft.Text(detalle)),
            ],
        )

    # ======================================================
    # BUSCAR
    # ======================================================

    def buscar_usuario(self, e):

        texto = self.buscar.value.lower()

        for fila in self.tabla.rows:

            usuario = fila.cells[1].content.value.lower()

            fila.visible = texto in usuario

        self.update()

    # ======================================================
    # FILTRAR
    # ======================================================

    def filtrar_accion(self, e):

        accion = self.filtro.value

        for fila in self.tabla.rows:

            valor = fila.cells[3].content.content.value

            if accion == "Todas":
                fila.visible = True
            else:
                fila.visible = valor == accion

        self.update()
