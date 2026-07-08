import flet as ft


def ReportesView():
    return ft.Column(controls=[_ReportesView()])


class _ReportesView(ft.Container):
    def __init__(self):
        super().__init__()

        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        self.content = ft.Column(
            controls=[
                self.header(),
                ft.Container(height=20),
                self.filters_section(),
                ft.Container(height=20),
                self.report_area(),
            ]
        )

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

    def filters_section(self):
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
                        spacing=10,
                        controls=[
                            self.report_button("Bodegas/Productos", ft.Icons.WAREHOUSE),
                            self.report_button("Ventas", ft.Icons.SHOPPING_CART),
                            self.report_button("Ventas Realizadas", ft.Icons.BAR_CHART),
                            self.report_button(
                                "Productos por Bodega", ft.Icons.INVENTORY
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Dropdown(
                                width=180,
                                label="Mes",
                                value="Marzo",
                                options=[
                                    ft.DropdownOption("Enero"),  #  fixed
                                    ft.DropdownOption("Febrero"),  #  fixed
                                    ft.DropdownOption("Marzo"),  #  fixed
                                ],
                            ),
                            ft.Dropdown(
                                width=180,
                                label="Año",
                                value="2026",
                                options=[
                                    ft.DropdownOption("2024"),  #  fixed
                                    ft.DropdownOption("2025"),  #  fixed
                                    ft.DropdownOption("2026"),  #  fixed
                                ],
                            ),
                            ft.ElevatedButton(
                                "Generar Reporte",
                                bgcolor="#d32f2f",
                                color="white",
                                height=45,
                            ),
                            ft.ElevatedButton(
                                "Exportar CSV",
                                icon=ft.Icons.DOWNLOAD,
                                bgcolor="#4caf50",
                                color="white",
                                height=45,
                            ),
                        ],
                    ),
                ],
            ),
        )

    def report_button(self, title, icon):
        return ft.Container(
            padding=12,
            border_radius=10,
            bgcolor="#f8f8f8",
            border=ft.border.all(1, "#e0e0e0"),
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(icon, size=18, color="#444"),
                    ft.Text(title, size=12),
                ],
            ),
        )

    def report_area(self):
        return ft.Container(
            expand=True,
            bgcolor="white",
            border_radius=15,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color=ft.Colors.BLACK12,
            ),
            alignment=ft.Alignment(0, 0),  #  fixed
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        ft.Icons.INSERT_CHART_OUTLINED,
                        size=60,
                        color="#d0d0d0",
                    ),
                    ft.Text(
                        "SELECCIONE UN TIPO DE REPORTE",
                        size=14,
                        color="#999",
                        weight=ft.FontWeight.W_500,
                    ),
                ],
            ),
        )
