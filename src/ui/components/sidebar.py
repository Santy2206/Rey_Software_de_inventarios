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
            ft.Column(
                spacing=5,
                controls=[
                    ft.Text("👑 REY", size=24, weight="bold", color="white"),
                    ft.Text("Inventarios", color="white70", size=12),
                ],
            ),
            ft.Divider(color="white24"),
            self._item(ft.Icons.DASHBOARD, "Dashboard", "dashboard"),
            self._item(ft.Icons.WAREHOUSE, "Bodegas", "BODEGAS"),
            self._item(ft.Icons.INVENTORY_2, "Productos", "PRODUCTOS"),
            self._item(ft.Icons.SWAP_HORIZ, "Movimientos", "MOVIMIENTOS"),
            self._item(ft.Icons.SHOPPING_CART, "Ventas", "VENTAS"),
            self._item(ft.Icons.PEOPLE, "Clientes", "CLIENTES"),
            self._item(ft.Icons.BAR_CHART, "Reportes", "REPORTES"),
            self._item(ft.Icons.DESCRIPTION, "Bitácora", "BITACORA"),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Cerrar sesión",
                icon=ft.Icons.LOGOUT,
                width=180,
                bgcolor="#8b0015",
                color="white",
                on_click=lambda _: self._on_logout(),
            ),
        ]

        self.width = 220
        self.bgcolor = "#b3001b"
        self.padding = 20
        self.content = ft.Column(
            expand=True,
            spacing=20,
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
                container.bgcolor = "#7a0016"  # más oscuro que el sidebar
                label.weight = ft.FontWeight.BOLD
            else:
                container.bgcolor = None
                label.weight = ft.FontWeight.W_500

        try:
            self.update()
        except Exception:
            # Puede ocurrir antes de que el sidebar esté montado
            pass
