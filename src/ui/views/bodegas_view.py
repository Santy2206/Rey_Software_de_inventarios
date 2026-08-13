import threading
import flet as ft
from src.services.bodegas_service import BodegasService

_CARD_COLORS = ["#f5b400", "#c2185b", "#2563eb", "#16a34a", "#7c3aed"]


def BodegasView():
    return ft.Column(controls=[_BodegasView()])


class _BodegasView(ft.Container):

    def __init__(self):
        super().__init__()
        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        # ── Estado interno ──────────────────────────────────────────────────
        self._bodegas: list[dict] = []
        self._bodega_editando: dict | None = None

        # ── Controles de texto actualizables ───────────────────────────────
        self._total_text = ft.Text("…", size=16, weight=ft.FontWeight.BOLD)
        self._fecha_text = ft.Text("…", size=16, weight=ft.FontWeight.BOLD)

        # ── Fila de tarjetas + indicador de carga ───────────────────────────
        self._cards_row = ft.Row(spacing=15, wrap=True)
        self._loading_ring = ft.ProgressRing(width=32, height=32, visible=True)
        self._cards_area = ft.Column(
            controls=[
                # Mientras carga: spinner centrado
                ft.Row(
                    [self._loading_ring],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                self._cards_row,
            ]
        )

        # Campos del formulario
        self._campo_nombre = ft.TextField(
            label="Nombre de la bodega",
            hint_text='Ej: "Bodega Principal"',
            border_radius=10,
        )
        self._campo_tipo = ft.TextField(
            label="Tipo",
            hint_text='Ej: "Fragancias", "General"',
            border_radius=10,
        )

        # ── Diálogo modal
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(""),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[self._campo_nombre, self._campo_tipo],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo),
                ft.ElevatedButton(
                    "Guardar",
                    bgcolor="#9eff8f",
                    color="black",
                    on_click=self._guardar_bodega,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # ── SnackBar
        self._snackbar = ft.SnackBar(
            content=ft.Text(""),
            show_close_icon=True,
        )

        # ── Layout principal ────────────────────────────────────────────────
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

    # ── Lifecycle hook: se llama cuando el widget YA está montado en la página ──
    def did_mount(self):
        """
        Punto correcto para:
          1. Registrar dialog y snackbar en page.overlay (una sola vez).
          2. Arrancar la carga de datos en un hilo de fondo.
        """
        # FIX 1 — agregar dialog al overlay una sola vez
        self.page.overlay.append(self._dialog)

        # FIX 2 — agregar snackbar al overlay (no al Column)
        self.page.overlay.append(self._snackbar)

        self.page.update()

        # FIX 3 — cargar datos en segundo plano para no bloquear la UI
        threading.Thread(target=self._cargar_bodegas, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # Carga de datos (corre en Thread separado)
    # ─────────────────────────────────────────────────────────────────────────

    def _cargar_bodegas(self):
        """
        Llama al servicio en un hilo de fondo.
        Cuando termina, actualiza la UI en el hilo principal con page.update().
        """
        result = BodegasService.get_all()

        # Ocultar spinner
        self._loading_ring.visible = False

        if result["success"]:
            self._bodegas = result["data"]
        else:
            self._bodegas = []
            if "Error" in result["message"]:
                self._mostrar_snack(result["message"], error=True)

        self._refrescar_cards()  # reconstruye las tarjetas
        self._actualizar_stats()  # actualiza contadores
        self.page.update()  # UN solo update al final 

    # ─────────────────────────────────────────────────────────────────────────
    # Construcción de tarjetas dinámicas
    # ─────────────────────────────────────────────────────────────────────────

    def _refrescar_cards(self):
        self._cards_row.controls.clear()
        for i, bodega in enumerate(self._bodegas):
            color = _CARD_COLORS[i % len(_CARD_COLORS)]
            self._cards_row.controls.append(self._warehouse_card(bodega, color))

    def _actualizar_stats(self):
        from datetime import datetime

        self._total_text.value = str(len(self._bodegas))
        self._fecha_text.value = datetime.now().strftime("%d/%m/%Y %I:%M %p")

    # ─────────────────────────────────────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────────────────────────────────────

    def _header_section(self):
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            "Bodegas", size=24, weight=ft.FontWeight.BOLD, color="#222"
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
                            padding=ft.padding.symmetric(horizontal=12, vertical=8),
                            content=ft.Row(
                                spacing=5,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.CHECK_CIRCLE, size=16, color="green"
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
                            on_click=self._abrir_dialogo_crear,
                        ),
                    ],
                ),
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Tarjeta individual de bodega
    # ─────────────────────────────────────────────────────────────────────────

    def _warehouse_card(self, bodega: dict, color: str):
        nombre = bodega.get("nombre", "Sin nombre")
        tipo = bodega.get("tipo", "—")

        return ft.Container(
            width=260,
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
                                            ft.Icons.WAREHOUSE, color=color
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
                                            ft.Text(tipo, size=11, color="grey"),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Container(
                                bgcolor="#f7f7f7",
                                padding=8,
                                border_radius=10,
                                content=ft.Icon(
                                    ft.Icons.VERIFIED, size=16, color=color
                                ),
                            ),
                        ],
                    ),
                    ft.Container(
                        height=8, border_radius=10, bgcolor=color, opacity=0.25
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.FilledButton(
                                "Editar",
                                icon=ft.Icons.EDIT,
                                bgcolor=color,
                                color="white",
                                expand=True,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8)
                                ),
                                #  b=bodega captura el valor correcto en el closure
                                on_click=lambda e, b=bodega: self._abrir_dialogo_editar(
                                    b
                                ),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_color="red",
                                tooltip="Eliminar bodega",
                                on_click=lambda e, bid=bodega[
                                    "id"
                                ], nom=nombre: self._eliminar_bodega(bid, nom),
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
                ft.Container(
                    expand=2,
                    height=180,
                    bgcolor="white",
                    border_radius=15,
                    padding=20,
                    shadow=ft.BoxShadow(
                        spread_radius=1, blur_radius=8, color=ft.Colors.BLACK12
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
                                alignment=ft.Alignment(0, 0),
                                content=ft.Icon(ft.Icons.ADD, size=30, color="grey"),
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
                                on_click=self._abrir_dialogo_crear,
                            ),
                        ],
                    ),
                ),
                ft.Column(
                    expand=1,
                    controls=[
                        self._info_card(
                            "Bodegas registradas", self._total_text, "#ffe8a3"
                        ),
                        ft.Container(height=10),
                        self._info_card(
                            "Última actualización", self._fecha_text, "#dcecff"
                        ),
                    ],
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
                        controls=[ft.Text(title, size=12, color="grey"), value_widget],
                    ),
                    ft.Container(width=35, height=35, border_radius=10, bgcolor=color),
                ],
            ),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Diálogos
    # ─────────────────────────────────────────────────────────────────────────

    def _abrir_dialogo_crear(self, e=None):
        self._bodega_editando = None
        self._campo_nombre.value = ""
        self._campo_tipo.value = ""
        self._dialog.title = ft.Text("Nueva Bodega")
        # FIX 1: NO hacemos page.overlay.append() aquí — ya está en el overlay desde did_mount
        self._dialog.open = True
        self.page.update()

    def _abrir_dialogo_editar(self, bodega: dict):
        self._bodega_editando = bodega
        self._campo_nombre.value = bodega.get("nombre", "")
        self._campo_tipo.value = bodega.get("tipo", "")
        self._dialog.title = ft.Text(f"Editar: {bodega.get('nombre')}")
        # FIX 1: solo toggleamos open, no volvemos a hacer append
        self._dialog.open = True
        self.page.update()

    def _cerrar_dialogo(self, e=None):
        self._dialog.open = False
        self.page.update()

    # ─────────────────────────────────────────────────────────────────────────
    # CRUD — delegan al servicio, luego recargan en background
    # ─────────────────────────────────────────────────────────────────────────

    def _guardar_bodega(self, e):
        nombre = self._campo_nombre.value.strip()
        tipo = self._campo_tipo.value.strip()

        if not nombre or not tipo:
            self._mostrar_snack("⚠️ Nombre y Tipo son obligatorios.", error=True)
            self.page.update()
            return

        self._cerrar_dialogo()

        # FIX 3: la escritura + recarga también van en un hilo
        def _worker():
            if self._bodega_editando is None:
                result = BodegasService.create(nombre=nombre, tipo=tipo)
            else:
                result = BodegasService.update(
                    bodega_id=self._bodega_editando["id"],
                    nombre=nombre,
                    tipo=tipo,
                )
            self._mostrar_snack(result["message"], error=not result["success"])
            if result["success"]:
                self._loading_ring.visible = True
                self.page.update()
                self._cargar_bodegas()

        threading.Thread(target=_worker, daemon=True).start()

    def _eliminar_bodega(self, bodega_id: str, nombre: str):
        def _worker():
            result = BodegasService.delete(bodega_id=bodega_id)
            self._mostrar_snack(result["message"], error=not result["success"])
            if result["success"]:
                self._loading_ring.visible = True
                self.page.update()
                self._cargar_bodegas()

        threading.Thread(target=_worker, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    # Feedback
    # ─────────────────────────────────────────────────────────────────────────

    def _mostrar_snack(self, mensaje: str, error: bool = False):
        # FIX 2: SnackBar está en page.overlay, no en el Column — ahora funciona
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        self.page.update()
