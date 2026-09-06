import threading
import flet as ft
from src.services.auth_service import AuthService
from src.services.bodegas_service import BodegasService
from src.ui.components.status_header import StatusHeader
from src.ui.components.page_header import PageHeader

_CARD_COLORS = ["#f5b400", "#c2185b", "#2563eb", "#16a34a", "#7c3aed"]
_PALABRA_ELIMINAR = "eliminar"


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
        self._bodega_pendiente_eliminar: dict | None = None
        self._bodega_pendiente_duplicar: dict | None = None
        self._overlays_registrados = False

        # ── Controles de texto actualizables ───────────────────────────────
        self._total_text = ft.Text("…", size=16, weight=ft.FontWeight.BOLD)
        self._fecha_text = ft.Text("…", size=16, weight=ft.FontWeight.BOLD)

        # ── Fila de tarjetas + indicador de carga ───────────────────────────
        self._cards_row = ft.Row(spacing=15, wrap=True)
        self._cards_row_sec = ft.Row(spacing=15, wrap=True)
        self._loading_ring = ft.ProgressRing(width=32, height=32, visible=True)
        self._cards_area = ft.Column(
            spacing=14,
            controls=[
                # Mientras carga: spinner centrado
                ft.Row(
                    [self._loading_ring],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Text(
                    "Principales",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color="#3730A3",
                ),
                self._cards_row,
                ft.Divider(height=10),
                ft.Text(
                    "Secundarias",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color="#6B7280",
                ),
                self._cards_row_sec,
            ],
        )

        # Campos del formulario (reutilizados al abrir diálogos)
        self._campo_nombre = ft.TextField(
            label="Nombre de la bodega",
            hint_text='Ej: "Bodega Principal"',
            border_radius=10,
            width=360,
        )
        self._campo_tipo = ft.Dropdown(
            label="Tipo",
            options=[
                ft.DropdownOption(key="General", text="General"),
                ft.DropdownOption(key="Fragancias", text="Fragancias"),
            ],
            border_radius=10,
            width=360,
        )
        self._campo_principal = ft.Checkbox(
            label="Bodega principal",
            value=False,
        )
        self._campo_cuentas = ft.TextField(
            label="Cuentas Elisa vinculadas",
            hint_text='Ej: "41353804, 41353802" o "Solo ingresos y traslados"',
            border_radius=10,
            width=360,
        )
        self._campo_password_editar = ft.TextField(
            label="Contraseña de su sesión",
            hint_text="Confirme su identidad para editar",
            password=True,
            can_reveal_password=True,
            border_radius=10,
            width=360,
        )

        # Campo para duplicar bodega
        self._campo_nombre_duplicar = ft.TextField(
            label="Nombre de la nueva bodega",
            hint_text='Ej: "Copia de Fragancias Bodega"',
            border_radius=10,
            width=360,
        )

        # Campos de seguridad para eliminar
        self._campo_password_eliminar = ft.TextField(
            label="Contraseña de su sesión",
            hint_text="Confirme su identidad para eliminar",
            password=True,
            can_reveal_password=True,
            border_radius=10,
            width=360,
        )
        self._campo_palabra_eliminar = ft.TextField(
            label=f'Escriba "{_PALABRA_ELIMINAR}" para confirmar',
            hint_text=_PALABRA_ELIMINAR,
            border_radius=10,
            width=360,
        )
        self._texto_eliminar = ft.Text("", size=13, color="#b71c1c", width=360)
        self._ayuda_seguridad_editar = ft.Text(
            "Por seguridad, confirme su contraseña para guardar cambios.",
            size=12,
            color="grey",
            width=360,
        )
        self._ayuda_seguridad_eliminar = ft.Text(
            "Esta acción es permanente. Confirme su contraseña y "
            f'escriba la palabra "{_PALABRA_ELIMINAR}".',
            size=12,
            color="grey",
            width=360,
        )
        self._error_dialogo = ft.Text("", size=12, color="#d32f2f", width=360, visible=False)

        # ── Barra de estado
        self._status_header = StatusHeader()

        # Diálogos se construyen al abrir (Flet refresca mejor así)
        self._dialog = None
        self._dialog_eliminar = None
        self._dialog_duplicar = None

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
          1. Registrar snackbar en page.overlay (una sola vez).
          2. Arrancar la carga de datos en un hilo de fondo.
        """
        if not self._overlays_registrados:
            self.page.overlay.append(self._snackbar)
            self._overlays_registrados = True

        self.page.update()

        # FIX 3 — cargar datos en segundo plano para no bloquear la UI
        self._status_header.load(self.page)
        threading.Thread(target=self._cargar_bodegas, daemon=True).start()

    def _mostrar_dialogo(self, dlg: ft.AlertDialog):
        """Abre un AlertDialog con el API actual de Flet (show_dialog)."""
        self._set_error_dialogo("")
        if dlg not in self.page.overlay:
            self.page.overlay.append(dlg)
        # Flet 0.84: show_dialog / pop_dialog gestionan el stack de diálogos
        if hasattr(self.page, "show_dialog"):
            self.page.show_dialog(dlg)
        else:
            dlg.open = True
            self.page.update()

    def _ocultar_dialogo(self, dlg: ft.AlertDialog | None):
        if dlg is None:
            return
        try:
            if hasattr(self.page, "pop_dialog"):
                self.page.pop_dialog()
            else:
                dlg.open = False
                self.page.update()
        except Exception:
            dlg.open = False
            try:
                self.page.update()
            except Exception:
                pass

    def _set_error_dialogo(self, mensaje: str):
        """Muestra u oculta el error dentro del diálogo abierto (visible sobre el modal)."""
        self._error_dialogo.value = mensaje or ""
        self._error_dialogo.visible = bool(mensaje)
        if self._campo_password_editar:
            self._campo_password_editar.error_text = (
                mensaje if mensaje and "contraseña" in mensaje.lower() else None
            )
        if self._campo_password_eliminar:
            self._campo_password_eliminar.error_text = (
                mensaje if mensaje and "contraseña" in mensaje.lower() else None
            )
        if self._campo_palabra_eliminar and mensaje and "eliminar" in mensaje.lower():
            self._campo_palabra_eliminar.error_text = mensaje
        elif self._campo_palabra_eliminar:
            self._campo_palabra_eliminar.error_text = None
        try:
            self.page.update()
        except Exception:
            pass

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
        self._cards_row_sec.controls.clear()
        principales = [b for b in self._bodegas if b.get("es_principal")]
        secundarias = [b for b in self._bodegas if not b.get("es_principal")]
        for i, bodega in enumerate(principales):
            color = _CARD_COLORS[i % len(_CARD_COLORS)]
            self._cards_row.controls.append(self._warehouse_card(bodega, color))
        for i, bodega in enumerate(secundarias):
            color = _CARD_COLORS[i % len(_CARD_COLORS)]
            self._cards_row_sec.controls.append(self._warehouse_card(bodega, color))

    def _actualizar_stats(self):
        from datetime import datetime

        self._total_text.value = str(len(self._bodegas))
        self._fecha_text.value = datetime.now().strftime("%d/%m/%Y %I:%M %p")

    # ─────────────────────────────────────────────────────────────────────────
    # Header
    # ─────────────────────────────────────────────────────────────────────────

    def _header_section(self):
        return PageHeader(
            title="Bodegas",
            subtitle="Gestiona todas las bodegas del sistema",
            status_control=self._status_header.control,
            action_buttons=[
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
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Tarjeta individual de bodega
    # ─────────────────────────────────────────────────────────────────────────

    def _warehouse_card(self, bodega: dict, color: str):
        nombre = bodega.get("nombre", "Sin nombre")
        tipo = bodega.get("tipo", "—")
        cuentas = (bodega.get("cuentas_elisa") or "").strip()

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
                    ft.Text(
                        f"Cuentas Elisa: {cuentas}" if cuentas else "Cuentas Elisa: —",
                        size=11,
                        color="#4B5563",
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
                                icon=ft.Icons.CONTENT_COPY,
                                icon_color=color,
                                tooltip="Duplicar bodega y productos",
                                on_click=lambda e, b=bodega: self._abrir_dialogo_duplicar(
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
        self._campo_tipo.value = None
        self._campo_principal.value = False
        self._campo_password_editar.value = ""
        self._campo_password_editar.error_text = None
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nueva Bodega"),
            content=ft.Column(
                tight=True,
                spacing=12,
                width=360,
                controls=[
                    self._campo_nombre,
                    self._campo_tipo,
                    self._campo_principal,
                    self._error_dialogo,
                ],
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
        self._mostrar_dialogo(self._dialog)

    def _abrir_dialogo_editar(self, bodega: dict):
        self._bodega_editando = bodega
        self._campo_nombre.value = bodega.get("nombre", "")
        tipo_actual = (bodega.get("tipo") or "").strip()
        self._campo_tipo.value = (
            tipo_actual if tipo_actual in ("General", "Fragancias") else None
        )
        self._campo_principal.value = bool(bodega.get("es_principal"))
        self._campo_cuentas.value = bodega.get("cuentas_elisa") or ""
        self._campo_password_editar.value = ""
        self._campo_password_editar.error_text = None
        self._dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Editar: {bodega.get('nombre')}"),
            content=ft.Column(
                tight=True,
                spacing=12,
                width=360,
                controls=[
                    self._campo_nombre,
                    self._campo_tipo,
                    self._campo_principal,
                    self._campo_cuentas,
                    self._ayuda_seguridad_editar,
                    self._campo_password_editar,
                    self._error_dialogo,
                ],
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
        self._mostrar_dialogo(self._dialog)

    def _cerrar_dialogo(self, e=None):
        self._ocultar_dialogo(self._dialog)
        self._dialog = None
        self._campo_password_editar.value = ""
        self._campo_password_editar.error_text = None
        self._set_error_dialogo("")

    def _abrir_dialogo_duplicar(self, bodega: dict):
        self._bodega_pendiente_duplicar = bodega
        self._campo_nombre_duplicar.value = f"Copia de {bodega.get('nombre', '')}"
        self._dialog_duplicar = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Duplicar: {bodega.get('nombre')}"),
            content=ft.Column(
                tight=True,
                spacing=12,
                width=360,
                controls=[
                    ft.Text(
                        "Se creará una nueva bodega con los mismos productos.",
                        size=13,
                        color="grey",
                    ),
                    self._campo_nombre_duplicar,
                    self._error_dialogo,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_duplicar),
                ft.ElevatedButton(
                    "Duplicar",
                    bgcolor="#2196F3",
                    color="white",
                    on_click=self._confirmar_duplicar_bodega,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._mostrar_dialogo(self._dialog_duplicar)

    def _cerrar_dialogo_duplicar(self, e=None):
        self._ocultar_dialogo(self._dialog_duplicar)
        self._dialog_duplicar = None
        self._bodega_pendiente_duplicar = None
        self._campo_nombre_duplicar.value = ""
        self._set_error_dialogo("")

    def _confirmar_duplicar_bodega(self, e=None):
        bodega = self._bodega_pendiente_duplicar
        if not bodega:
            self._cerrar_dialogo_duplicar()
            return

        nuevo_nombre = (self._campo_nombre_duplicar.value or "").strip()
        bodega_id = str(bodega["id"])
        self._cerrar_dialogo_duplicar()

        def _worker():
            try:
                result = BodegasService.duplicar(
                    bodega_id=bodega_id,
                    nuevo_nombre=nuevo_nombre,
                )
            except Exception as ex:
                result = {"success": False, "message": f"Error al duplicar: {ex}"}
            self._mostrar_snack(result["message"], error=not result["success"])
            if result["success"]:
                self._loading_ring.visible = True
                self.page.update()
                self._cargar_bodegas()

        threading.Thread(target=_worker, daemon=True).start()

    def _abrir_dialogo_eliminar(self, bodega: dict):
        self._bodega_pendiente_eliminar = bodega
        nombre = bodega.get("nombre", "esta bodega")
        self._texto_eliminar.value = (
            f'¿Seguro que desea eliminar la bodega "{nombre}"?'
        )
        self._campo_password_eliminar.value = ""
        self._campo_palabra_eliminar.value = ""
        self._campo_password_eliminar.error_text = None
        self._campo_palabra_eliminar.error_text = None
        self._dialog_eliminar = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar bodega"),
            content=ft.Column(
                tight=True,
                spacing=12,
                width=360,
                controls=[
                    self._texto_eliminar,
                    self._ayuda_seguridad_eliminar,
                    self._campo_password_eliminar,
                    self._campo_palabra_eliminar,
                    self._error_dialogo,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_eliminar),
                ft.ElevatedButton(
                    "Eliminar definitivamente",
                    bgcolor="#d32f2f",
                    color="white",
                    on_click=self._confirmar_eliminar_bodega,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._mostrar_dialogo(self._dialog_eliminar)

    def _cerrar_dialogo_eliminar(self, e=None):
        self._ocultar_dialogo(self._dialog_eliminar)
        self._dialog_eliminar = None
        self._bodega_pendiente_eliminar = None
        self._campo_password_eliminar.value = ""
        self._campo_palabra_eliminar.value = ""
        self._campo_password_eliminar.error_text = None
        self._campo_palabra_eliminar.error_text = None
        self._set_error_dialogo("")

    # ─────────────────────────────────────────────────────────────────────────
    # CRUD — delegan al servicio, luego recargan en background
    # ─────────────────────────────────────────────────────────────────────────

    def _guardar_bodega(self, e):
        nombre = (self._campo_nombre.value or "").strip()
        tipo = (self._campo_tipo.value or "").strip()
        es_principal = bool(self._campo_principal.value)

        if not nombre or not tipo:
            self._set_error_dialogo("Nombre y Tipo son obligatorios.")
            return

        # Editar requiere revalidar la contraseña de la sesión
        if self._bodega_editando is not None:
            password = (self._campo_password_editar.value or "").strip()
            auth = AuthService.verificar_password_sesion(password)
            if not auth["success"]:
                self._set_error_dialogo(auth["message"])
                return

        editando = self._bodega_editando
        self._cerrar_dialogo()

        def _worker():
            try:
                if editando is None:
                    result = BodegasService.create(
                        nombre=nombre, tipo=tipo, es_principal=es_principal
                    )
                else:
                    result = BodegasService.update(
                        bodega_id=str(editando["id"]),
                        nombre=nombre,
                        tipo=tipo,
                        es_principal=es_principal,
                        cuentas_elisa=self._campo_cuentas.value or None,
                    )
            except Exception as ex:
                result = {"success": False, "message": f"Error al guardar: {ex}"}
            self._mostrar_snack(result["message"], error=not result["success"])
            if result["success"]:
                self._loading_ring.visible = True
                self.page.update()
                self._cargar_bodegas()

        threading.Thread(target=_worker, daemon=True).start()

    def _eliminar_bodega(self, bodega_id: str, nombre: str):
        bodega = next((b for b in self._bodegas if b.get("id") == bodega_id), None)
        if bodega is None:
            bodega = {"id": bodega_id, "nombre": nombre}
        self._abrir_dialogo_eliminar(bodega)

    def _confirmar_eliminar_bodega(self, e=None):
        bodega = self._bodega_pendiente_eliminar
        if not bodega:
            self._cerrar_dialogo_eliminar()
            return

        password = (self._campo_password_eliminar.value or "").strip()
        palabra = (self._campo_palabra_eliminar.value or "").strip().lower()

        if palabra != _PALABRA_ELIMINAR:
            self._set_error_dialogo(
                f'Para eliminar debe escribir exactamente "{_PALABRA_ELIMINAR}".'
            )
            return

        auth = AuthService.verificar_password_sesion(password)
        if not auth["success"]:
            self._set_error_dialogo(auth["message"])
            return

        bodega_id = str(bodega["id"])
        self._cerrar_dialogo_eliminar()

        def _worker():
            try:
                result = BodegasService.delete(bodega_id=bodega_id)
            except Exception as ex:
                result = {"success": False, "message": f"Error al eliminar: {ex}"}
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
