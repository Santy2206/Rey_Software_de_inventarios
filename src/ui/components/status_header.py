"""
Barra de estado reutilizable para las vistas.

Muestra:
  - Rol del usuario autenticado
  - Estado de sincronización con Supabase: Sincronizado / Pendientes (N) / Sin conexión
  - Botón de sincronización directa
  - Botón de cambio de modo (escritorio ↔ navegador)

El badge de sincronización es clickable cuando hay registros pendientes
y muestra un diálogo con el desglose por tabla.

La carga del estado corre en un hilo de fondo para no bloquear la UI.
"""

import threading

import flet as ft

from src.services.auth_service import AuthService
from src.sync.sync_service import SyncService
from src.ui.components.view_switcher import ViewSwitcher


class StatusHeader:
    """Control de estado de usuario, sincronización y acciones globales."""

    def __init__(self):
        self._page = None
        self._detalle_pendientes = {}
        self._total_pendientes = 0
        self._view_switcher = ViewSwitcher()

        self._sync_text = ft.Text(
            "Cargando...",
            size=12,
            color="green",
            weight=ft.FontWeight.BOLD,
        )
        self._sync_icon = ft.Icon(
            ft.Icons.CLOUD,
            color="green",
            size=16,
        )
        self._rol_text = ft.Text(
            "—",
            size=11,
            color="grey",
        )

        self._sync_badge = ft.Container(
            bgcolor="#E8FFF0",
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            content=ft.Row(
                spacing=5,
                controls=[
                    self._sync_icon,
                    self._sync_text,
                ],
            ),
            on_click=self._mostrar_pendientes,
        )

        self._btn_vista = ft.ElevatedButton(
            content="Abrir en navegador",
            icon=ft.Icons.OPEN_IN_BROWSER,
            bgcolor="#2196F3",
            color="white",
            height=35,
            on_click=lambda _: self._view_switcher.switch(),
        )

        self._btn_sync = ft.ElevatedButton(
            "Sincronizar ahora",
            icon=ft.Icons.CLOUD_SYNC,
            bgcolor="#2196F3",
            color="white",
            height=35,
            visible=False,
            on_click=self._on_sincronizar,
        )

        self._user_badge = ft.Container(
            bgcolor="white",
            border_radius=15,
            padding=10,
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.CircleAvatar(
                        bgcolor="#b3001b",
                        content=ft.Text("A", color="white"),
                    ),
                    ft.Column(
                        spacing=0,
                        controls=[
                            ft.Text(
                                "Usuario",
                                weight=ft.FontWeight.BOLD,
                                size=12,
                            ),
                            self._rol_text,
                        ],
                    ),
                ],
            ),
        )

        self.control = ft.Row(
            spacing=10,
            controls=[
                self._btn_vista,
                self._sync_badge,
                self._btn_sync,
                self._user_badge,
            ],
        )

    def _on_sincronizar(self, _e):
        if not self._page or self._btn_sync.disabled:
            return

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Sincronizando"),
            content=ft.Row(
                spacing=15,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.ProgressRing(color="#2196F3", width=28, height=28),
                    ft.Text("Enviando datos a Supabase...", size=14),
                ],
            ),
        )
        self._page.overlay.append(dlg)
        self._page.show_dialog(dlg)

        def _on_result(result):
            if not self._page:
                return
            self._page.run_task(self._mostrar_notificacion, dlg, result)

        SyncService.sync_pendientes_background(callback=_on_result)

    def _mostrar_pendientes(self, _e=None):
        """Abre el diálogo de registros pendientes cuando hay datos por sync."""
        if not self._page or self._total_pendientes <= 0:
            return

        filas = [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(tabla.capitalize(), size=14),
                    ft.Text(str(cantidad), weight=ft.FontWeight.BOLD),
                ],
            )
            for tabla, cantidad in sorted(self._detalle_pendientes.items())
            if cantidad > 0
        ]

        if not filas:
            filas = [ft.Text("No hay registros pendientes.", size=14)]

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Registros pendientes"),
            content=ft.Column(
                spacing=10,
                height=min(250, max(80, len(filas) * 40)),
                tight=True,
                scroll=ft.ScrollMode.AUTO,
                controls=filas,
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self._cerrar_dialogo(dlg)),
                ft.ElevatedButton(
                    "Sincronizar ahora",
                    icon=ft.Icons.CLOUD_SYNC,
                    bgcolor="#2196F3",
                    color="white",
                    on_click=lambda e: self._sincronizar_desde_pendientes(dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.overlay.append(dlg)
        self._page.show_dialog(dlg)

    def _cerrar_dialogo(self, dlg):
        dlg.open = False
        self._page.update()

    def _sincronizar_desde_pendientes(self, dlg):
        if not self._page:
            return
        dlg.open = False
        self._page.update()

        loading = ft.AlertDialog(
            modal=True,
            title=ft.Text("Sincronizando"),
            content=ft.Row(
                spacing=15,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.ProgressRing(color="#2196F3", width=28, height=28),
                    ft.Text("Enviando datos a Supabase...", size=14),
                ],
            ),
        )
        self._page.overlay.append(loading)
        self._page.show_dialog(loading)

        def _on_result(result):
            if not self._page:
                return
            self._page.run_task(self._mostrar_notificacion, loading, result)

        SyncService.sync_pendientes_background(callback=_on_result)

    async def _mostrar_notificacion(self, dlg: ft.AlertDialog, result: dict):
        if not self._page:
            return
        try:
            success = result.get("success", False)
            mensaje = result.get("message", "Sincronización finalizada")

            # Cerrar diálogo de carga
            dlg.open = False
            self._page.update()

            # Notificación tipo Toast
            sb = ft.SnackBar(
                ft.Text(mensaje),
                bgcolor="green" if success else "red",
                show_close_icon=True,
                duration=5000,
            )
            self._page.show_dialog(sb)

            # Recargar estado
            self.load(self._page)
        except Exception:
            # Si algo falla en la notificación, al menos recargar estado
            try:
                self.load(self._page)
            except Exception:
                pass

    def load(self, page: ft.Page):
        """Carga rol y estado de sincronización."""
        self._page = page
        self._view_switcher.set_page(page)

        rol = AuthService.get_rol() or "—"
        self._rol_text.value = rol.capitalize()

        # Actualizar botón de cambio de modo
        if page.web:
            self._btn_vista.content = "Abrir en escritorio"
            self._btn_vista.icon = ft.Icons.DESKTOP_WINDOWS
        else:
            self._btn_vista.content = "Abrir en navegador"
            self._btn_vista.icon = ft.Icons.OPEN_IN_BROWSER

        res = SyncService.pendientes_por_tabla()
        if res.get("success"):
            detalle = res.get("data", {})
            self._detalle_pendientes = detalle
            self._total_pendientes = sum(detalle.values())

            if self._total_pendientes > 0:
                self._sync_text.value = f"Pendientes ({self._total_pendientes})"
                self._sync_text.color = "orange"
                self._sync_icon.color = "orange"
                self._sync_badge.bgcolor = "#FFF7ED"
                self._sync_badge.ink = True
                self._sync_badge.mouse_cursor = ft.MouseCursor.CLICK
                self._btn_sync.visible = True
            else:
                self._sync_text.value = "Sincronizado"
                self._sync_text.color = "green"
                self._sync_icon.color = "green"
                self._sync_badge.bgcolor = "#E8FFF0"
                self._sync_badge.ink = False
                self._sync_badge.mouse_cursor = None
                self._btn_sync.visible = False
        else:
            self._detalle_pendientes = {}
            self._total_pendientes = 0
            self._sync_text.value = "Sin conexión"
            self._sync_text.color = "red"
            self._sync_icon.color = "red"
            self._sync_badge.bgcolor = "#FEE2E2"
            self._sync_badge.ink = False
            self._sync_badge.mouse_cursor = None
            self._btn_sync.visible = False

        page.update()
