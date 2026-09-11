"""
Vista de Usuarios.

Lista los usuarios del sistema y permite cambiar el rol de cada uno
(administrador / vendedor / bodeguero). El cambio de rol queda
registrado en la bitácora como CAMBIO_ROL.

Sigue el mismo patrón que bodegas_view.py / bitacora_view.py:
  - Función pública UsuariosView() que envuelve la clase privada.
  - Clase _UsuariosView hereda de ft.Container.
  - La carga de datos corre en un hilo de fondo (threading), disparada
    desde did_mount().
  - Dialog y SnackBar se registran en page.overlay desde did_mount().

Reglas:
    - SIN lógica de negocio — solo diseño e interacción de interfaz.
    - SIN llamadas directas a la base de datos.
    - SIN ft.app() — esta vista es montada por dashboard_view.py.
"""

import threading

import flet as ft

from src.services.auth_service import AuthService
from src.services.usuarios_service import UsuariosService, ROLES_VALIDOS
from src.ui.components.status_header import StatusHeader
from src.ui.components.page_header import PageHeader

_COLORES_ROL = {
    "administrador": ("#FEE2E2", "#B91C1C"),
    "vendedor": ("#DCFCE7", "#15803D"),
    "bodeguero": ("#DBEAFE", "#1D4ED8"),
    "empleado": ("#F3E8FF", "#7E22CE"),
}


def UsuariosView():
    return ft.Column(controls=[_UsuariosView()])


class _UsuariosView(ft.Container):

    def __init__(self):
        super().__init__()
        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        self._usuarios: list[dict] = []
        self._usuario_editando: dict | None = None

        # ── Barra de estado
        self._status_header = StatusHeader()

        # ── SnackBar
        self._snackbar = ft.SnackBar(content=ft.Text(""), show_close_icon=True)

        # ── Diálogo de crear usuario
        self._campo_nombre = ft.TextField(
            label="Nombre *",
            hint_text='Ej: "María López"',
            border_radius=10,
        )
        self._campo_email = ft.TextField(
            label="Correo / usuario *",
            hint_text="Ej: maria@perfumas.com",
            border_radius=10,
        )
        self._campo_password = ft.TextField(
            label="Contraseña inicial *",
            password=True,
            can_reveal_password=True,
            border_radius=10,
        )
        self._campo_rol_nuevo = ft.Dropdown(
            label="Rol *",
            border_radius=10,
            options=[
                ft.DropdownOption(key="administrador", text="Administrador"),
                ft.DropdownOption(key="empleado", text="Empleado"),
            ],
            value="empleado",
        )
        self._dialog_crear = ft.AlertDialog(
            modal=True,
            title=ft.Text("Crear usuario"),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[
                    self._campo_nombre,
                    self._campo_email,
                    self._campo_password,
                    self._campo_rol_nuevo,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_crear),
                ft.ElevatedButton(
                    "Guardar",
                    bgcolor="#9eff8f",
                    color="black",
                    on_click=self._guardar_usuario,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # ── Diálogo de cambio de rol
        self._campo_rol = ft.Dropdown(
            label="Nuevo rol",
            border_radius=10,
            options=[
                ft.DropdownOption(key=r, text=r.capitalize())
                for r in ROLES_VALIDOS
            ],
        )
        self._dialog_rol = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cambiar rol"),
            content=ft.Column(
                tight=True,
                spacing=12,
                controls=[self._campo_rol],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_rol),
                ft.ElevatedButton(
                    "Guardar",
                    bgcolor="#9eff8f",
                    color="black",
                    on_click=self._guardar_rol,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # ── Tabla
        self._total = ft.Text(
            "0 usuarios",
            color="#4338CA",
            weight=ft.FontWeight.BOLD,
        )
        self._tabla = ft.DataTable(
            expand=True,
            border=ft.border.all(1, "#eeeeee"),
            border_radius=10,
            vertical_lines=ft.BorderSide(1, "#eeeeee"),
            horizontal_lines=ft.BorderSide(1, "#eeeeee"),
            heading_row_color="#fafafa",
            columns=[
                ft.DataColumn(ft.Text("Nombre")),
                ft.DataColumn(ft.Text("Email")),
                ft.DataColumn(ft.Text("Rol")),
                ft.DataColumn(ft.Text("Acciones")),
            ],
            rows=[],
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                self._header(),
                ft.Container(height=20),
                self._seccion_tabla(),
            ],
        )

    # ── Lifecycle ───────────────────────────────────────────────────────
    def did_mount(self):
        self.page.overlay.append(self._dialog_rol)
        self.page.overlay.append(self._dialog_crear)
        self.page.overlay.append(self._snackbar)
        self.page.update()
        self._status_header.load(self.page)
        threading.Thread(target=self._cargar_usuarios, daemon=True).start()

    def _cargar_usuarios(self):
        resultado = UsuariosService.get_all()
        self._usuarios = resultado.get("data", []) if resultado.get("success") else []
        self._refrescar_tabla()
        self.page.update()

    # ======================================================
    # HEADER
    # ======================================================

    def _header(self):
        es_admin = AuthService.get_rol() == "administrador"
        action_buttons = [
            ft.ElevatedButton(
                "Crear usuario",
                icon=ft.Icons.PERSON_ADD,
                bgcolor="#9eff8f",
                color="black",
                on_click=self._abrir_dialogo_crear,
            )
        ]
        return PageHeader(
            title="Usuarios",
            subtitle="Gestión de usuarios y roles del sistema",
            status_control=self._status_header.control,
            action_buttons=action_buttons if es_admin else None,
        )

    # ======================================================
    # TABLA
    # ======================================================

    def _seccion_tabla(self):
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
                                        "Usuarios del sistema",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        "Cambia el rol de un usuario",
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
                                            ft.Icons.PEOPLE,
                                            color="#4338CA",
                                            size=16,
                                        ),
                                        self._total,
                                    ],
                                ),
                            ),
                        ],
                    ),
                    ft.Divider(),
                    self._tabla,
                ],
            ),
        )

    def _refrescar_tabla(self):
        self._tabla.rows = [self._crear_fila(u) for u in self._usuarios]
        self._total.value = f"{len(self._tabla.rows)} usuarios"

    def _crear_fila(self, usuario: dict):
        rol = (usuario.get("rol") or "—").lower()
        fondo, texto = _COLORES_ROL.get(rol, ("#F3F4F6", "#374151"))

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(usuario.get("name") or "—")),
                ft.DataCell(ft.Text(usuario.get("email") or "—")),
                ft.DataCell(
                    ft.Container(
                        bgcolor=fondo,
                        border_radius=20,
                        padding=6,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(
                            rol.capitalize(),
                            color=texto,
                            weight=ft.FontWeight.BOLD,
                            size=11,
                        ),
                    )
                ),
                ft.DataCell(
                    ft.IconButton(
                        icon=ft.Icons.EDIT,
                        icon_color="#4338CA",
                        tooltip="Cambiar rol",
                        on_click=lambda e, u=usuario: self._abrir_dialogo_rol(u),
                    )
                ),
            ]
        )

    # ======================================================
    # CAMBIO DE ROL
    # ======================================================

    def _abrir_dialogo_rol(self, usuario: dict):
        self._usuario_editando = usuario
        self._campo_rol.value = (usuario.get("rol") or "").lower() or None
        self._dialog_rol.title = ft.Text(
            f"Cambiar rol de {usuario.get('name', '')}"
        )
        self._dialog_rol.open = True
        self.page.update()

    def _cerrar_dialogo_rol(self, e=None):
        self._usuario_editando = None
        self._dialog_rol.open = False
        self.page.update()

    def _guardar_rol(self, e=None):
        usuario = self._usuario_editando
        nuevo_rol = self._campo_rol.value
        if not usuario or not nuevo_rol:
            self._mostrar_snack("⚠️ Selecciona un rol.", error=True)
            return

        self._cerrar_dialogo_rol()

        def _worker():
            result = UsuariosService.cambiar_rol(
                usuario_id=str(usuario["id"]),
                nuevo_rol=nuevo_rol,
            )
            self._mostrar_snack(result["message"], error=not result["success"])
            if result["success"]:
                self._cargar_usuarios()

        threading.Thread(target=_worker, daemon=True).start()

    # ======================================================
    # FEEDBACK
    # ======================================================

    def _abrir_dialogo_crear(self, e=None):
        self._campo_nombre.value = ""
        self._campo_email.value = ""
        self._campo_password.value = ""
        self._campo_rol_nuevo.value = "empleado"
        self._dialog_crear.open = True
        self.page.update()

    def _cerrar_dialogo_crear(self, e=None):
        self._dialog_crear.open = False
        self.page.update()

    def _guardar_usuario(self, e=None):
        nombre = (self._campo_nombre.value or "").strip()
        email = (self._campo_email.value or "").strip()
        password = (self._campo_password.value or "").strip()
        rol = (self._campo_rol_nuevo.value or "").strip()

        if not nombre or not email or not password or not rol:
            self._mostrar_snack("⚠️ Complete todos los campos.", error=True)
            return

        self._cerrar_dialogo_crear()

        def _worker():
            result = UsuariosService.create(
                nombre=nombre,
                email=email,
                password=password,
                rol=rol,
            )
            self._mostrar_snack(result["message"], error=not result["success"])
            if result.get("success"):
                self._cargar_usuarios()

        threading.Thread(target=_worker, daemon=True).start()

    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        if self.page:
            self.page.update()
