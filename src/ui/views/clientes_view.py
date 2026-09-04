"""
Vista de Clientes.

Permite listar, crear, editar y eliminar clientes del sistema.
Sigue el mismo patrón que bodegas_view.py:
  - Función pública ClientesView() que envuelve la clase privada.
  - Clase _ClientesView hereda de ft.Container.
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

from src.services.clientes_service import ClientesService
from src.ui.components.status_header import StatusHeader
from src.ui.components.page_header import PageHeader

_CARD_COLORS = ["#2563eb", "#16a34a", "#f5b400", "#c2185b", "#7c3aed"]


def ClientesView():
    return ft.Column(controls=[_ClientesView()])


class _ClientesView(ft.Container):

    def __init__(self):
        super().__init__()
        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        # ── Estado interno ───────────────────────────────────────────────────
        self._clientes: list[dict] = []
        self._cliente_editando: dict | None = None

        # ── Controles de texto actualizables ─────────────────────────────────
        self._total_text = ft.Text("…", size=16, weight=ft.FontWeight.BOLD)
        self._fecha_text = ft.Text("…", size=16, weight=ft.FontWeight.BOLD)

        # ── Fila de tarjetas + indicador de carga ────────────────────────────
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
            label="Nombre *",
            hint_text='Ej: "Juan Pérez"',
            border_radius=10,
        )
        self._campo_telefono = ft.TextField(
            label="Teléfono",
            hint_text="Ej: 3001234567",
            border_radius=10,
        )
        self._campo_email = ft.TextField(
            label="Email",
            hint_text="Ej: correo@ejemplo.com",
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
                    self._campo_telefono,
                    self._campo_email,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo),
                ft.ElevatedButton(
                    "Guardar",
                    bgcolor="#9eff8f",
                    color="black",
                    on_click=self._guardar_cliente,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # ── Barra de estado
        self._status_header = StatusHeader()

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
                self._cards_area,
                ft.Container(height=20),
                self._bottom_section(),
            ],
            spacing=0,
            expand=True,
        )

    # ── Lifecycle hook ───────────────────────────────────────────────────────
    def did_mount(self):
        self.page.overlay.append(self._dialog)
        self.page.overlay.append(self._snackbar)
        self.page.update()
        self._status_header.load(self.page)
        threading.Thread(target=self._cargar_clientes, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # Carga de datos (corre en Thread separado)
    # ─────────────────────────────────────────────────────────────────────────

    def _cargar_clientes(self):
        result = ClientesService.get_all()

        # Ocultar spinner
        self._loading_ring.visible = False

        if result.get("success"):
            self._clientes = result.get("data", [])
        else:
            self._clientes = []
            if "Error" in result.get("message", ""):
                self._mostrar_snack(result["message"], error=True)

        self._refrescar_cards()
        self._actualizar_stats()
        self.page.update()  # UN solo update al final

    # ─────────────────────────────────────────────────────────────────────────
    # Construcción de tarjetas dinámicas
    # ─────────────────────────────────────────────────────────────────────────

    def _refrescar_cards(self):
        self._cards_row.controls.clear()
        for i, cliente in enumerate(self._clientes):
            color = _CARD_COLORS[i % len(_CARD_COLORS)]
            self._cards_row.controls.append(self._cliente_card(cliente, color))

    def _actualizar_stats(self):
        from datetime import datetime

        self._total_text.value = str(len(self._clientes))
        self._fecha_text.value = datetime.now().strftime("%d/%m/%Y %I:%M %p")

    # ─────────────────────────────────────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────────────────────────────────────

    def _header_section(self):
        return PageHeader(
            title="Clientes",
            subtitle="Gestiona los clientes del sistema",
            status_control=self._status_header.control,
            action_buttons=[
                ft.ElevatedButton(
                    "Crear Cliente",
                    icon=ft.Icons.ADD,
                    bgcolor="#9eff8f",
                    color="black",
                    on_click=self._abrir_dialogo_crear,
                ),
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Tarjeta individual de cliente
    # ─────────────────────────────────────────────────────────────────────────

    def _cliente_card(self, cliente: dict, color: str):
        nombre = cliente.get("nombre", "Sin nombre")
        telefono = cliente.get("telefono") or "—"
        email = cliente.get("email") or "—"

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
                                            ft.Icons.PERSON, color=color
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
                                                email,
                                                size=11,
                                                color="grey",
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Text(f"Tel: {telefono}", size=12, color="grey"),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.FilledButton(
                                "Editar",
                                icon=ft.Icons.EDIT,
                                bgcolor=color,
                                color="white",
                                expand=True,
                                on_click=lambda e, c=cliente: self._abrir_dialogo_editar(
                                    c
                                ),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color="red",
                                tooltip="Eliminar cliente",
                                on_click=lambda e, cid=cliente["id"], nom=nombre: self._eliminar_cliente(
                                    cid, nom
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
                    "Clientes registrados", self._total_text, "#ffe8a3"
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
    # Diálogos
    # ─────────────────────────────────────────────────────────────────────────

    def _abrir_dialogo_crear(self, e=None):
        self._cliente_editando = None
        self._campo_nombre.value = ""
        self._campo_telefono.value = ""
        self._campo_email.value = ""
        self._dialog.title = ft.Text("Nuevo Cliente")
        self._dialog.open = True
        self.page.update()

    def _abrir_dialogo_editar(self, cliente: dict):
        self._cliente_editando = cliente
        self._campo_nombre.value = cliente.get("nombre", "")
        self._campo_telefono.value = cliente.get("telefono", "")
        self._campo_email.value = cliente.get("email", "")
        self._dialog.title = ft.Text(f"Editar: {cliente.get('nombre')}")
        self._dialog.open = True
        self.page.update()

    def _cerrar_dialogo(self, e=None):
        self._dialog.open = False
        self.page.update()

    # ─────────────────────────────────────────────────────────────────────────
    # CRUD — delegan al servicio, luego recargan en background
    # ─────────────────────────────────────────────────────────────────────────

    def _guardar_cliente(self, e):
        nombre = (self._campo_nombre.value or "").strip()
        telefono = (self._campo_telefono.value or "").strip()
        email = (self._campo_email.value or "").strip()

        if not nombre:
            self._mostrar_snack("⚠️ El nombre es obligatorio.", error=True)
            self.page.update()
            return

        self._cerrar_dialogo()

        def _worker():
            if self._cliente_editando is None:
                result = ClientesService.create(
                    nombre=nombre, telefono=telefono, email=email
                )
            else:
                result = ClientesService.update(
                    cliente_id=self._cliente_editando["id"],
                    nombre=nombre,
                    telefono=telefono,
                    email=email,
                )
            self._mostrar_snack(
                result.get("message", ""), error=not result.get("success")
            )
            if result.get("success"):
                self._loading_ring.visible = True
                self.page.update()
                self._cargar_clientes()

        threading.Thread(target=_worker, daemon=True).start()

    def _eliminar_cliente(self, cliente_id: str, nombre: str):
        def _worker():
            result = ClientesService.delete(cliente_id=cliente_id)
            self._mostrar_snack(
                result.get("message", ""), error=not result.get("success")
            )
            if result.get("success"):
                self._loading_ring.visible = True
                self.page.update()
                self._cargar_clientes()

        threading.Thread(target=_worker, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # Feedback
    # ─────────────────────────────────────────────────────────────────────────

    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        self.page.update()
