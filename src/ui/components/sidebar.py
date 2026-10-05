import flet as ft


class Sidebar(ft.Container):
    """
    Sidebar de navegación con resaltado del panel activo.

    Uso:
        sidebar = Sidebar(on_navigate=load_content, on_logout=handle_logout)
        sidebar.set_active("dashboard")
    """

    def __init__(self, on_navigate, on_logout, active="dashboard"):
        super().__init__()
        self._on_navigate = on_navigate
        self._on_logout = on_logout
        self._items: dict[str, ft.Container] = {}

        menu_controls = [
            ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        border=ft.border.all(2, "#FFC200"),
                        border_radius=12,
                        padding=5,
                        bgcolor="#000000",
                        content=ft.Column(
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Image(
                                    src="corona.png",
                                    width=55,
                                    height=28,
                                    fit=ft.BoxFit.CONTAIN,
                                ),
                                ft.Text(
                                    "REY",
                                    size=20,
                                    weight="bold",
                                    color="#FFC200",
                                ),
                                ft.Text(
                                    "SOFTWARE DE INVENTARIOS",
                                    size=8,
                                    weight="bold",
                                    color="#FFC200",
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                        ),
                    ),
                ],
            ),
            ft.Divider(color="#FFC200", height=1),
            self._item(ft.Icons.DASHBOARD, "Dashboard", "dashboard"),
            self._item(ft.Icons.WAREHOUSE, "Bodegas", "BODEGAS"),
            self._item(ft.Icons.INVENTORY_2, "Productos", "PRODUCTOS"),
            self._item(ft.Icons.SWAP_HORIZ, "Movimientos", "MOVIMIENTOS"),
            self._item(ft.Icons.SHOPPING_CART, "Ventas", "VENTAS"),
            self._item(ft.Icons.FACT_CHECK, "Revisión ventas", "REVISION_VENTAS"),
            self._item(ft.Icons.PEOPLE, "Clientes", "CLIENTES"),
            self._item(ft.Icons.BAR_CHART, "Reportes", "REPORTES"),
            self._item(ft.Icons.DESCRIPTION, "Bitácora", "BITACORA"),
            self._item(ft.Icons.MANAGE_ACCOUNTS, "Usuarios", "USUARIOS"),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Cerrar sesión",
                icon=ft.Icons.LOGOUT,
                width=180,
                bgcolor="#FFC200", color="black",
                on_click=lambda _: self._on_logout(),
            ),
        ]

        self.width = 220
        self.bgcolor="#000000"
        self.padding = 20
        self.content = ft.Column(
            expand=True,
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            controls=menu_controls,
        )

        self.set_active(active)

    def _item(self, icon, text, page_name):
        label = ft.Text(
            text,
            color="white",
            size=14,
            weight=ft.FontWeight.W_500,
        )
        icon_ctrl = ft.Icon(icon, color="white", size=20)

        container = ft.Container(
            padding=10,
            border_radius=10,
            content=ft.Row(
                controls=[icon_ctrl, label],
            ),
            on_click=lambda e, name=page_name: self._on_navigate(name),
        )
        self._items[page_name] = container
        return container

    def set_active(self, page_name: str):
        """Resalta el ítem del menú que corresponde al panel actual."""
        for name, container in self._items.items():
            label = container.content.controls[1]
            if name == page_name:
                container.bgcolor="#1A1A1A"  # más oscuro que el sidebar
                label.weight = ft.FontWeight.BOLD
            else:
                container.bgcolor = None
                label.weight = ft.FontWeight.W_500

        try:
            self.update()
        except Exception:
            # Puede ocurrir antes de que el sidebar esté montado
            pass
