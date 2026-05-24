
import flet as ft


class BodegasView(ft.Container):
    def __init__(self):
        super().__init__()

        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        self.content = ft.Column(
            controls=[
                self.header_section(),
                ft.Container(height=15),
                self.cards_section(),
                ft.Container(height=20),
                self.bottom_cards(),
            ],
            spacing=0,
            expand=True,
        )

    def header_section(self):
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            "Bodegas",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="#222",
                        ),
                        ft.Text(
                            "Gestiona todas las bodegas del sistema",
                            size=12,
                            color="grey",
                        ),
                    ],
                ),
                ft.Row(
                    spacing=10,
                    controls=[
                        ft.Container(
                            bgcolor="#e8fff0",
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
                                        size=16,
                                        color="green",
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
                        ft.ElevatedButton(
                            "Crear Bodega",
                            icon=ft.Icons.ADD,
                            bgcolor="#9eff8f",
                            color="black",
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=10)
                            ),
                        ),
                    ],
                ),
            ],
        )

    def warehouse_card(self, title, products, color):
        return ft.Container(
            expand=True,
            bgcolor="white",
            border_radius=15,
            padding=15,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color=ft.Colors.BLACK12,
            ),
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        width=40,
                                        height=40,
                                        border_radius=10,
                                        bgcolor="#f0f0f0",
                                        alignment=ft.alignment.center,
                                        content=ft.Icon(
                                            ft.Icons.WAREHOUSE,
                                            color=color,
                                        ),
                                    ),
                                    ft.Column(
                                        spacing=0,
                                        controls=[
                                            ft.Text(
                                                title,
                                                weight=ft.FontWeight.BOLD,
                                                size=14,
                                            ),
                                            ft.Text(
                                                "Bodega activa",
                                                size=11,
                                                color="grey",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Container(
                                bgcolor="#f7f7f7",
                                padding=8,
                                border_radius=10,
                                content=ft.Text(
                                    str(products),
                                    weight=ft.FontWeight.BOLD,
                                    size=18,
                                ),
                            ),
                        ],
                    ),
                    ft.Container(
                        height=10,
                        border_radius=10,
                        bgcolor="#f0f0f0",
                        content=ft.Container(
                            width=180,
                            border_radius=10,
                            bgcolor=color,
                        ),
                    ),
                    ft.FilledButton(
                        "Gestionar bodega",
                        bgcolor=color,
                        color="white",
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8)
                        ),
                    ),
                ],
            ),
        )

    def cards_section(self):
        return ft.Row(
            spacing=15,
            controls=[
                self.warehouse_card(
                    "Fragancias",
                    124,
                    "#f5b400",
                ),
                self.warehouse_card(
                    "Rola Negra",
                    78,
                    "#c2185b",
                ),
                self.warehouse_card(
                    "General",
                    312,
                    "#2563eb",
                ),
            ],
        )

    def bottom_cards(self):
        return ft.Row(
            spacing=15,
            controls=[
                ft.Container(
                    expand=2,
                    height=180,
                    bgcolor="white",
                    border_radius=15,
                    padding=20,
                    shadow=ft.BoxShadow(
                        spread_radius=1,
                        blur_radius=8,
                        color=ft.Colors.BLACK12,
                    ),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=60,
                                height=60,
                                border_radius=30,
                                bgcolor="#f3f3f3",
                                alignment=ft.alignment.center,
                                content=ft.Icon(
                                    ft.Icons.ADD,
                                    size=30,
                                    color="grey",
                                ),
                            ),
                            ft.Text(
                                "Añadir nueva bodega",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Crear una nueva bodega para organizar productos",
                                size=11,
                                color="grey",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.ElevatedButton(
                                "Crear bodega",
                                bgcolor="#ffd400",
                                color="black",
                            ),
                        ],
                    ),
                ),
                ft.Column(
                    expand=1,
                    controls=[
                        self.info_card("Bodegas", "3", "#ffe8a3"),
                        ft.Container(height=10),
                        self.info_card("Productos", "514", "#d5ffd0"),
                        ft.Container(height=10),
                        self.info_card(
                            "Última actualización",
                            "24/03/2026 02:55 p. m.",
                            "#dcecff",
                        ),
                    ],
                ),
            ],
        )

    def info_card(self, title, value, color):
        return ft.Container(
            bgcolor="white",
            border_radius=15,
            padding=15,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=6,
                color=ft.Colors.BLACK12,
            ),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                title,
                                size=12,
                                color="grey",
                            ),
                            ft.Text(
                                value,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                    ),
                    ft.Container(
                        width=35,
                        height=35,
                        border_radius=10,
                        bgcolor=color,
                    ),
                ],
            ),
        )