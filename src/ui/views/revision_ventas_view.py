"""
Vista de revisión de importación Elisa (Fase 2).

Muestra filas pendientes de ventas_import_raw y permite:
  - Vincular a un producto existente (sugerido o búsqueda manual)
  - Crear un producto nuevo a partir de los atributos
  - Descartar la fila (motivo obligatorio)

También expone un diálogo de fusión de productos duplicados
(FusionProductoService) con contraseña + palabra FUSIONAR.

Patrón: _RevisionVentasView(ft.Container) + wrapper, did_mount + threading.
SIN lógica de negocio ni acceso directo a BD.
"""

from __future__ import annotations

import json
import threading

import flet as ft

from src.services.bodegas_service import BodegasService
from src.services.auth_service import AuthService
from src.services.clientes_resolucion_service import ClientesResolucionService
from src.services.fusion_producto_service import (
    FusionProductoService,
    PALABRA_CONFIRMACION,
)
from src.services.ventas_excepciones_service import VentasExcepcionesService
from src.services.ventas_proceso_service import VentasProcesoService
from src.services.ventas_resolucion_service import VentasResolucionService
from src.ui.components.page_header import PageHeader
from src.ui.components.status_header import StatusHeader

_CAT_LABELS = {
    "productos_pendientes": "Productos no resueltos",
    "conflictos_cliente": "Conflictos de cliente",
    "errores_proceso": "Errores de procesamiento",
    "sobrantes_caja": "Sobrantes de caja (41353899)",
    "duplicados_omitidos": "Duplicados omitidos",
    "stock_negativo": "Stock negativo",
}


def RevisionVentasView():
    return ft.Column(controls=[_RevisionVentasView()])


class _RevisionVentasView(ft.Container):

    def __init__(self):
        super().__init__()
        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        self._filas: list[dict] = []
        self._conflictos_cliente: list[dict] = []
        self._bodegas: list[dict] = []
        self._fila_actual: dict | None = None
        self._candidatos_actuales: list[dict] = []

        self._status_header = StatusHeader()
        self._snackbar = ft.SnackBar(content=ft.Text(""), show_close_icon=True)
        self._loading = ft.ProgressRing(visible=False, width=24, height=24)

        self._lbl_resumen = ft.Text(
            "0 productos · 0 clientes", color="#4338CA", weight=ft.FontWeight.BOLD
        )
        self._lista = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        self._lista_clientes = ft.Column(
            spacing=12, expand=True, scroll=ft.ScrollMode.AUTO
        )
        self._resumen_exc: dict = {}
        self._categoria_exc: str | None = None
        self._detalle_exc: list[dict] = []
        self._chips_exc = ft.Row(spacing=8, wrap=True, run_spacing=8)
        self._lista_exc = ft.Column(
            spacing=8, expand=True, scroll=ft.ScrollMode.AUTO, height=260
        )
        self._lbl_exc = ft.Text(
            "Excepciones: —", size=13, color="#6B7280", weight=ft.FontWeight.W_500
        )

        # --- Diálogo vincular ---
        self._buscar_producto = ft.TextField(
            label="Buscar producto",
            hint_text="Código o nombre",
            border_radius=10,
            on_submit=self._buscar_manual,
        )
        self._filtro_bodega_vincular = ft.Dropdown(
            label="Filtrar por bodega",
            hint_text="Todas",
            border_radius=10,
            options=[],
            on_select=self._buscar_manual,
        )
        self._lista_candidatos = ft.Column(spacing=6, tight=True, scroll=ft.ScrollMode.AUTO, height=220)
        self._dialog_vincular = ft.AlertDialog(
            modal=True,
            title=ft.Text("Vincular producto"),
            content=ft.Column(
                tight=True,
                spacing=10,
                width=420,
                controls=[
                    self._buscar_producto,
                    self._filtro_bodega_vincular,
                    ft.ElevatedButton(
                        "Buscar",
                        icon=ft.Icons.SEARCH,
                        on_click=self._buscar_manual,
                    ),
                    self._lista_candidatos,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_vincular),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # --- Diálogo crear ---
        self._campo_nombre_nuevo = ft.TextField(label="Nombre *", border_radius=10)
        self._campo_codigo_nuevo = ft.TextField(label="Código", border_radius=10)
        self._campo_bodega_nuevo = ft.Dropdown(label="Bodega *", border_radius=10, options=[])
        self._dialog_crear = ft.AlertDialog(
            modal=True,
            title=ft.Text("Crear producto nuevo"),
            content=ft.Column(
                tight=True,
                spacing=10,
                width=400,
                controls=[
                    self._campo_nombre_nuevo,
                    self._campo_codigo_nuevo,
                    self._campo_bodega_nuevo,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_crear),
                ft.ElevatedButton(
                    "Crear y vincular",
                    bgcolor="#16A34A",
                    color="white",
                    on_click=self._confirmar_crear,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # --- Diálogo descartar ---
        self._campo_motivo = ft.TextField(
            label="Motivo *",
            hint_text="Explica por qué se descarta",
            border_radius=10,
            multiline=True,
            min_lines=2,
        )
        self._dialog_descartar = ft.AlertDialog(
            modal=True,
            title=ft.Text("Descartar fila"),
            content=self._campo_motivo,
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_descartar),
                ft.ElevatedButton(
                    "Descartar",
                    bgcolor="#b3001b",
                    color="white",
                    on_click=self._confirmar_descartar,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # --- Diálogo fusión ---
        self._fusion_origen = ft.TextField(label="ID producto origen (duplicado)", border_radius=10)
        self._fusion_destino = ft.TextField(label="ID producto destino (se conserva)", border_radius=10)
        self._fusion_password = ft.TextField(
            label="Tu contraseña *",
            password=True,
            can_reveal_password=True,
            border_radius=10,
        )
        self._fusion_palabra = ft.TextField(
            label=f'Escribe "{PALABRA_CONFIRMACION}" *',
            border_radius=10,
        )
        self._dialog_fusion = ft.AlertDialog(
            modal=True,
            title=ft.Text("Fusionar productos"),
            content=ft.Column(
                tight=True,
                spacing=10,
                width=420,
                controls=[
                    ft.Text(
                        "Operación irreversible. Mueve movimientos, ventas e "
                        "importaciones del origen al destino y elimina el origen.",
                        size=12,
                        color="grey",
                    ),
                    self._fusion_origen,
                    self._fusion_destino,
                    self._fusion_password,
                    self._fusion_palabra,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self._cerrar_dialogo_fusion),
                ft.ElevatedButton(
                    "Fusionar",
                    bgcolor="#7C2D12",
                    color="white",
                    on_click=self._confirmar_fusion,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                self._header(),
                ft.Container(height=16),
                self._toolbar(),
                ft.Container(height=12),
                ft.Container(
                    expand=True,
                    bgcolor="white",
                    border_radius=15,
                    padding=16,
                    shadow=ft.BoxShadow(
                        spread_radius=1, blur_radius=8, color=ft.Colors.BLACK12
                    ),
                    content=ft.Column(
                        expand=True,
                        spacing=10,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(
                                        "Cola de revisión",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Row(
                                        spacing=8,
                                        controls=[self._loading, self._lbl_resumen],
                                    ),
                                ],
                            ),
                            ft.Divider(),
                            ft.Text(
                                "Productos pendientes",
                                size=14,
                                weight=ft.FontWeight.W_600,
                            ),
                            self._lista,
                            ft.Divider(),
                            ft.Text(
                                "Conflictos de clientes",
                                size=14,
                                weight=ft.FontWeight.W_600,
                            ),
                            self._lista_clientes,
                            ft.Divider(),
                            ft.Text(
                                "Reporte de excepciones (Fase 5)",
                                size=14,
                                weight=ft.FontWeight.W_600,
                            ),
                            self._lbl_exc,
                            self._chips_exc,
                            self._lista_exc,
                        ],
                    ),
                ),
            ],
        )

    # ------------------------------------------------------------------
    def did_mount(self):
        for d in (
            self._dialog_vincular,
            self._dialog_crear,
            self._dialog_descartar,
            self._dialog_fusion,
            self._snackbar,
        ):
            self.page.overlay.append(d)
        self.page.update()
        self._status_header.load(self.page)
        threading.Thread(target=self._cargar_inicial, daemon=True).start()

    def _header(self):
        return PageHeader(
            title="Revisión ventas",
            subtitle="Resolver productos y clientes de la importación Elisa",
            status_control=self._status_header.control,
            action_buttons=[
                ft.ElevatedButton(
                    "Resolver productos",
                    icon=ft.Icons.AUTO_FIX_HIGH,
                    bgcolor="#2196F3",
                    color="white",
                    height=40,
                    on_click=self._on_resolver_pendientes,
                ),
                ft.ElevatedButton(
                    "Resolver clientes",
                    icon=ft.Icons.PERSON_SEARCH,
                    bgcolor="#0D9488",
                    color="white",
                    height=40,
                    on_click=self._on_resolver_clientes,
                ),
                ft.ElevatedButton(
                    "Procesar ventas",
                    icon=ft.Icons.POINT_OF_SALE,
                    bgcolor="#b3001b",
                    color="white",
                    height=40,
                    on_click=self._on_procesar_ventas,
                ),
                ft.ElevatedButton(
                    "Fusionar productos",
                    icon=ft.Icons.MERGE,
                    bgcolor="#7C2D12",
                    color="white",
                    height=40,
                    on_click=self._abrir_dialogo_fusion,
                ),
                ft.ElevatedButton(
                    "Actualizar",
                    icon=ft.Icons.REFRESH,
                    bgcolor="#6B7280",
                    color="white",
                    height=40,
                    on_click=lambda e: threading.Thread(
                        target=self._cargar_pendientes, daemon=True
                    ).start(),
                ),
            ],
        )

    def _toolbar(self):
        return ft.Container(
            bgcolor="#EEF2FF",
            border_radius=12,
            padding=12,
            content=ft.Text(
                "Productos: filas pendientes de catálogo. "
                "Clientes: conflictos de cédula/nombre. "
                "Cuadres 41353899 no aparecen. Nada de esto mueve stock.",
                size=12,
                color="#3730A3",
            ),
        )

    # ------------------------------------------------------------------
    def _cargar_inicial(self):
        res_b = BodegasService.get_all()
        self._bodegas = res_b.get("data", []) if res_b.get("success") else []

        _PRINCIPALES = ("ENVASES", "VENTA FRAGANCIAS", "FRAGANCIAS BODEGA")

        def _label_bodega(b: dict) -> str:
            nombre = (b.get("nombre") or "—").strip()
            if nombre.upper() in _PRINCIPALES:
                return nombre
            cuentas = (b.get("cuentas_elisa") or "").strip()
            return f"{nombre} ({cuentas})" if cuentas else nombre

        self._campo_bodega_nuevo.options = [
            ft.DropdownOption(key=str(b["id"]), text=_label_bodega(b))
            for b in self._bodegas
        ]

        self._filtro_bodega_vincular.options = [
            ft.DropdownOption(key="", text="Todas")
        ] + [
            ft.DropdownOption(key=str(b["id"]), text=_label_bodega(b))
            for b in self._bodegas
        ]
        self._cargar_pendientes()

    def _cargar_pendientes(self):
        self._loading.visible = True
        try:
            if self.page:
                self.page.update()
        except Exception:
            pass

        res = VentasResolucionService.get_pendientes()
        self._filas = res.get("data", []) if res.get("success") else []
        res_c = ClientesResolucionService.get_conflictos()
        self._conflictos_cliente = (
            res_c.get("data", []) if res_c.get("success") else []
        )
        res_e = VentasExcepcionesService.resumen()
        self._resumen_exc = res_e.get("data") or {} if res_e.get("success") else {}
        self._refrescar_lista()
        self._loading.visible = False
        try:
            if self.page:
                self.page.update()
        except Exception:
            pass

    def _refrescar_lista(self):
        self._lista.controls.clear()
        self._lista_clientes.controls.clear()
        total_exc = self._resumen_exc.get("total_excepciones", 0)
        self._lbl_resumen.value = (
            f"{len(self._filas)} productos · "
            f"{len(self._conflictos_cliente)} clientes · "
            f"{total_exc} excepciones"
        )
        if not self._filas:
            self._lista.controls.append(
                ft.Text(
                    "No hay productos pendientes de revisión.",
                    color="grey",
                    italic=True,
                )
            )
        else:
            for fila in self._filas:
                self._lista.controls.append(self._tarjeta_fila(fila))

        if not self._conflictos_cliente:
            self._lista_clientes.controls.append(
                ft.Text(
                    "No hay conflictos de clientes.",
                    color="grey",
                    italic=True,
                )
            )
        else:
            for fila in self._conflictos_cliente:
                self._lista_clientes.controls.append(self._tarjeta_cliente(fila))

        self._pintar_chips_exc()
        self._pintar_detalle_exc()

    def _pintar_chips_exc(self):
        self._chips_exc.controls.clear()
        total = self._resumen_exc.get("total_excepciones", 0)
        self._lbl_exc.value = f"Excepciones totales: {total}"
        for key, label in _CAT_LABELS.items():
            n = int(self._resumen_exc.get(key) or 0)
            activo = self._categoria_exc == key
            self._chips_exc.controls.append(
                ft.Container(
                    bgcolor="#312E81" if activo else ("#EEF2FF" if n else "#F3F4F6"),
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    on_click=lambda e, k=key: self._abrir_categoria_exc(k),
                    content=ft.Text(
                        f"{label}: {n}",
                        size=12,
                        color="white" if activo else ("#3730A3" if n else "#9CA3AF"),
                        weight=ft.FontWeight.BOLD if n else ft.FontWeight.W_500,
                    ),
                )
            )

    def _abrir_categoria_exc(self, categoria: str):
        self._categoria_exc = categoria
        self._pintar_chips_exc()
        if self.page:
            self.page.update()

        def _worker():
            res = VentasExcepcionesService.get_detalle(categoria, limite=100)
            self._detalle_exc = res.get("data") or [] if res.get("success") else []
            self._pintar_detalle_exc()
            if self.page:
                self.page.update()

        threading.Thread(target=_worker, daemon=True).start()

    def _pintar_detalle_exc(self):
        self._lista_exc.controls.clear()
        if not self._categoria_exc:
            self._lista_exc.controls.append(
                ft.Text(
                    "Selecciona una categoría del reporte para ver el detalle.",
                    color="grey",
                    italic=True,
                )
            )
            return
        if not self._detalle_exc:
            self._lista_exc.controls.append(
                ft.Text("Sin registros en esta categoría.", color="grey", italic=True)
            )
            return

        cat = self._categoria_exc
        if cat == "stock_negativo":
            for p in self._detalle_exc:
                self._lista_exc.controls.append(
                    ft.Container(
                        bgcolor="#FEF2F2",
                        border=ft.border.all(1, "#FECACA"),
                        border_radius=10,
                        padding=10,
                        content=ft.Text(
                            f"{p.get('nombre') or '—'} [{p.get('codigo') or 's/c'}] · "
                            f"stock {p.get('stock_actual')} · "
                            f"{p.get('bodega_nombre') or '—'}",
                            size=12,
                        ),
                    )
                )
            return

        for fila in self._detalle_exc:
            if cat == "errores_proceso":
                extra = fila.get("error_proceso") or "—"
            elif cat == "sobrantes_caja":
                extra = f"crédito {fila.get('credito') or '0'}"
            elif cat == "duplicados_omitidos":
                extra = f"huella {(fila.get('huella') or '')[:12]}… · venta {fila.get('venta_id') or '—'}"
            elif cat == "conflictos_cliente":
                conf = fila.get("conflicto_cliente") or {}
                if isinstance(conf, dict):
                    extra = conf.get("motivo") or "conflicto"
                else:
                    extra = "conflicto"
            else:
                extra = fila.get("clave_busqueda") or fila.get("concepto_limpio") or "—"
            self._lista_exc.controls.append(
                ft.Container(
                    bgcolor="#F9FAFB",
                    border=ft.border.all(1, "#E5E7EB"),
                    border_radius=10,
                    padding=10,
                    content=ft.Column(
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Text(
                                f"Fila {fila.get('fila_origen')} · "
                                f"cta {fila.get('cuenta') or '—'} · "
                                f"{fila.get('identidad') or '—'}",
                                size=11,
                                color="grey",
                            ),
                            ft.Text(fila.get("concepto") or "—", size=13),
                            ft.Text(str(extra), size=11, color="#4B5563"),
                        ],
                    ),
                )
            )
    def _tarjeta_fila(self, fila: dict) -> ft.Container:
        attrs = fila.get("atributos") or {}
        if not isinstance(attrs, dict):
            attrs = {}
        candidatos = fila.get("candidatos") or []
        if not isinstance(candidatos, list):
            candidatos = []

        chips = []
        if attrs.get("categoria"):
            chips.append(self._chip(str(attrs["categoria"]), "#E0E7FF", "#3730A3"))
        if attrs.get("reclasificado"):
            chips.append(
                self._chip(
                    f"reclasificado (cta {attrs.get('cuenta_original') or '—'})",
                    "#FEE2E2",
                    "#991B1B",
                )
            )
        if attrs.get("corregido") and attrs.get("correcciones"):
            chips.append(
                self._chip(
                    "corregido: " + ", ".join(attrs["correcciones"][:3]),
                    "#FFEDD5",
                    "#9A3412",
                )
            )
        if attrs.get("nota"):
            chips.append(
                self._chip(f"nota: {attrs['nota']}", "#F3F4F6", "#374151")
            )
        if attrs.get("es_obsequio"):
            chips.append(self._chip("OBSEQUIO", "#EDE9FE", "#5B21B6"))
        if attrs.get("codigo") or (attrs.get("codigos") and len(attrs["codigos"]) == 1):
            cod = attrs.get("codigo") or attrs["codigos"][0]
            chips.append(self._chip(f"cód {cod}", "#DCFCE7", "#166534"))
        if attrs.get("es_combo"):
            chips.append(self._chip("combo", "#FEF3C7", "#92400E"))
        if attrs.get("envase"):
            chips.append(self._chip(str(attrs["envase"]), "#FCE7F3", "#9D174D"))
        if attrs.get("tamano_ml"):
            chips.append(self._chip(f"{attrs['tamano_ml']} ml", "#DBEAFE", "#1D4ED8"))

        cand_texts = []
        for c in candidatos[:5]:
            score = c.get("score")
            score_txt = f"{float(score):.0%}" if score is not None else "—"
            cand_texts.append(
                ft.Text(
                    f"• {c.get('nombre') or '—'} [{c.get('codigo') or 's/c'}] "
                    f"— {score_txt} ({c.get('motivo') or ''})",
                    size=12,
                )
            )
        if not cand_texts:
            cand_texts = [ft.Text("Sin candidatos sugeridos", size=12, color="grey")]

        fila_id = str(fila["id"])
        return ft.Container(
            bgcolor="#FAFAFA",
            border=ft.border.all(1, "#E5E7EB"),
            border_radius=12,
            padding=14,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                f"Fila {fila.get('fila_origen')} · cuenta {fila.get('cuenta') or '—'}",
                                size=12,
                                color="grey",
                            ),
                            ft.Text(
                                (fila.get("clave_busqueda") or "")[:60],
                                size=11,
                                color="#6B7280",
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=14,
                        wrap=True,
                        controls=[
                            ft.Text(
                                f"Fecha: {str(fila.get('fecha') or '—')[:10]}",
                                size=12,
                                color="#374151",
                            ),
                            ft.Text(
                                f"Valor: {fila.get('credito') if fila.get('credito') is not None else '—'}",
                                size=12,
                                color="#374151",
                            ),
                            ft.Text(
                                f"Cliente: {fila.get('nombre_tercero') or fila.get('nombre_cliente_limpio') or '—'}",
                                size=12,
                                color="#374151",
                            ),
                            ft.Text(
                                f"CC: {fila.get('identidad') or '—'}",
                                size=12,
                                color="#374151",
                            ),
                            ft.Text(
                                f"Tel: {fila.get('telefonos_tercero') or '—'}",
                                size=12,
                                color="#374151",
                            ),
                        ],
                    ),
                    ft.Text(
                        fila.get("concepto") or "—",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        f"Limpio: {fila.get('concepto_limpio') or '—'}",
                        size=12,
                        color="#374151",
                    ),
                    ft.Row(spacing=6, wrap=True, controls=chips),
                    ft.Text("Candidatos:", size=12, weight=ft.FontWeight.W_600),
                    *cand_texts,
                    ft.Row(
                        spacing=8,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.OutlinedButton(
                                "Vincular",
                                icon=ft.Icons.LINK,
                                on_click=lambda e, f=fila: self._abrir_dialogo_vincular(f),
                            ),
                            ft.ElevatedButton(
                                "Crear",
                                icon=ft.Icons.ADD,
                                bgcolor="#16A34A",
                                color="white",
                                on_click=lambda e, f=fila: self._abrir_dialogo_crear(f),
                            ),
                            ft.ElevatedButton(
                                "Descartar",
                                icon=ft.Icons.DELETE_OUTLINE,
                                bgcolor="#b3001b",
                                color="white",
                                on_click=lambda e, f=fila: self._abrir_dialogo_descartar(f),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _chip(self, text, bg, fg):
        return ft.Container(
            bgcolor=bg,
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=10, vertical=4),
            content=ft.Text(text, size=11, color=fg, weight=ft.FontWeight.BOLD),
        )

    # ------------------------------------------------------------------
    def _on_resolver_pendientes(self, e=None):
        self._loading.visible = True
        self.page.update()

        def _worker():
            res = VentasResolucionService.resolver_pendientes()
            self._mostrar_snack(res.get("message", ""), error=not res.get("success"))
            self._cargar_pendientes()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_resolver_clientes(self, e=None):
        self._loading.visible = True
        self.page.update()

        def _worker():
            res = ClientesResolucionService.resolver_pendientes()
            self._mostrar_snack(res.get("message", ""), error=not res.get("success"))
            self._cargar_pendientes()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_procesar_ventas(self, e=None):
        self._loading.visible = True
        self.page.update()

        def _worker():
            res = VentasProcesoService.procesar_pendientes(
                usuario_id=AuthService.get_usuario_id()
            )
            self._mostrar_snack(res.get("message", ""), error=not res.get("success"))
            self._cargar_pendientes()

        threading.Thread(target=_worker, daemon=True).start()

    def _tarjeta_cliente(self, fila: dict) -> ft.Container:
        conf = fila.get("conflicto_cliente") or {}
        if not isinstance(conf, dict):
            conf = {}
        motivo = conf.get("motivo") or "conflicto"
        detalle = []
        if conf.get("nombre_existente") or conf.get("nombre_nuevo"):
            detalle.append(
                ft.Text(
                    f"Existente: {conf.get('nombre_existente') or '—'}  |  "
                    f"Nuevo: {conf.get('nombre_nuevo') or '—'}",
                    size=12,
                )
            )
        if conf.get("similitud") is not None:
            detalle.append(
                ft.Text(
                    f"Similitud: {float(conf['similitud']):.0%}",
                    size=12,
                    color="#6B7280",
                )
            )
        if conf.get("motivo") == "sin_cedula":
            detalle.append(
                ft.Text("La fila no trae cédula válida.", size=12, color="#B45309")
            )

        fila_id = str(fila["id"])
        return ft.Container(
            bgcolor="#FFF7ED",
            border=ft.border.all(1, "#FDBA74"),
            border_radius=12,
            padding=14,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text(
                        f"Fila {fila.get('fila_origen')} · cédula "
                        f"{fila.get('identidad') or '—'} · {motivo}",
                        size=12,
                        color="grey",
                    ),
                    ft.Text(
                        fila.get("nombre_tercero") or "—",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        f"Limpio: {fila.get('nombre_cliente_limpio') or '—'} · "
                        f"código Elisa: {fila.get('codigo_elisa') or '—'}",
                        size=12,
                    ),
                    *detalle,
                    ft.Row(
                        spacing=8,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.OutlinedButton(
                                "Mantener existente",
                                icon=ft.Icons.CHECK,
                                on_click=lambda e, fid=fila_id: self._aceptar_cliente(
                                    fid
                                ),
                            ),
                            ft.ElevatedButton(
                                "Usar nombre del archivo",
                                icon=ft.Icons.EDIT,
                                bgcolor="#0D9488",
                                color="white",
                                on_click=lambda e, fid=fila_id: self._forzar_nombre(
                                    fid
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _aceptar_cliente(self, fila_id: str):
        def _worker():
            res = ClientesResolucionService.aceptar_cliente_existente(fila_id)
            self._mostrar_snack(res.get("message", ""), error=not res.get("success"))
            if res.get("success"):
                self._cargar_pendientes()

        threading.Thread(target=_worker, daemon=True).start()

    def _forzar_nombre(self, fila_id: str):
        def _worker():
            res = ClientesResolucionService.actualizar_nombre_y_vincular(fila_id)
            self._mostrar_snack(res.get("message", ""), error=not res.get("success"))
            if res.get("success"):
                self._cargar_pendientes()

        threading.Thread(target=_worker, daemon=True).start()

    # --- Vincular ---
    def _abrir_dialogo_vincular(self, fila: dict):
        self._fila_actual = fila
        self._buscar_producto.value = fila.get("clave_busqueda") or ""
        # Preselecciona la bodega sugerida por el grupo de la fila
        attrs = fila.get("atributos") or {}
        sug = attrs.get("bodega_sugerida") if isinstance(attrs, dict) else None
        bodega_id_sug = ""
        if sug:
            for b in self._bodegas:
                if (b.get("nombre") or "").strip().upper() == str(sug).strip().upper():
                    bodega_id_sug = str(b["id"])
                    break
        self._filtro_bodega_vincular.value = bodega_id_sug or None
        candidatos = fila.get("candidatos") or []
        if not isinstance(candidatos, list):
            candidatos = []
        self._candidatos_actuales = candidatos
        self._pintar_candidatos(candidatos)
        self._dialog_vincular.open = True
        self.page.update()

    def _cerrar_dialogo_vincular(self, e=None):
        self._dialog_vincular.open = False
        self._fila_actual = None
        self.page.update()

    def _pintar_candidatos(self, candidatos: list[dict]):
        self._lista_candidatos.controls.clear()
        if not candidatos:
            self._lista_candidatos.controls.append(
                ft.Text("Sin resultados", color="grey", italic=True)
            )
            return
        for c in candidatos:
            score = c.get("score")
            score_txt = f"{float(score):.0%}" if score is not None else ""
            pid = str(c["id"])
            self._lista_candidatos.controls.append(
                ft.ListTile(
                    title=ft.Text(c.get("nombre") or "—"),
                    subtitle=ft.Text(
                        f"{c.get('codigo') or 's/c'} · {c.get('bodega_nombre') or '—'} · {score_txt}"
                    ),
                    trailing=ft.ElevatedButton(
                        "Usar",
                        on_click=lambda e, p=pid: self._confirmar_vincular(p),
                    ),
                )
            )

    def _buscar_manual(self, e=None):
        texto = self._buscar_producto.value or ""
        bodega_id = self._filtro_bodega_vincular.value or None

        def _worker():
            res = VentasResolucionService.buscar_productos_manual(
                texto, bodega_id=bodega_id
            )
            self._candidatos_actuales = res.get("data") or []
            self._pintar_candidatos(self._candidatos_actuales)
            if self.page:
                self.page.update()

        threading.Thread(target=_worker, daemon=True).start()

    def _confirmar_vincular(self, producto_id: str):
        fila = self._fila_actual
        self._cerrar_dialogo_vincular()
        if not fila:
            return

        def _worker():
            res = VentasResolucionService.vincular(str(fila["id"]), producto_id)
            self._mostrar_snack(res.get("message", ""), error=not res.get("success"))
            if res.get("success"):
                self._cargar_pendientes()

        threading.Thread(target=_worker, daemon=True).start()

    # --- Crear ---
    def _abrir_dialogo_crear(self, fila: dict):
        self._fila_actual = fila
        attrs = fila.get("atributos") or {}
        if not isinstance(attrs, dict):
            attrs = {}
        self._campo_nombre_nuevo.value = (
            attrs.get("nombre")
            or fila.get("concepto_limpio")
            or fila.get("concepto")
            or ""
        )
        self._campo_codigo_nuevo.value = attrs.get("codigo") or (
            (attrs.get("codigos") or [None])[0] if attrs.get("codigos") else ""
        ) or ""
        bodega_sug = attrs.get("bodega_sugerida")
        valor_sug = None
        if bodega_sug:
            for b in self._bodegas:
                if (b.get("nombre") or "").strip().upper() == str(bodega_sug).strip().upper():
                    valor_sug = str(b["id"])
                    break
        self._campo_bodega_nuevo.value = valor_sug
        self._dialog_crear.open = True
        self.page.update()

    def _cerrar_dialogo_crear(self, e=None):
        self._dialog_crear.open = False
        self._fila_actual = None
        self.page.update()

    def _confirmar_crear(self, e=None):
        fila = self._fila_actual
        nombre = (self._campo_nombre_nuevo.value or "").strip()
        codigo = (self._campo_codigo_nuevo.value or "").strip() or None
        bodega_id = self._campo_bodega_nuevo.value
        if not fila:
            return
        if not nombre or not bodega_id:
            self._mostrar_snack("Nombre y bodega son obligatorios.", error=True)
            return
        self._cerrar_dialogo_crear()

        def _worker():
            res = VentasResolucionService.crear_producto_nuevo(
                fila_id=str(fila["id"]),
                bodega_id=bodega_id,
                nombre=nombre,
                codigo=codigo,
            )
            self._mostrar_snack(res.get("message", ""), error=not res.get("success"))
            if res.get("success"):
                self._cargar_pendientes()

        threading.Thread(target=_worker, daemon=True).start()

    # --- Descartar ---
    def _abrir_dialogo_descartar(self, fila: dict):
        self._fila_actual = fila
        self._campo_motivo.value = ""
        self._dialog_descartar.open = True
        self.page.update()

    def _cerrar_dialogo_descartar(self, e=None):
        self._dialog_descartar.open = False
        self._fila_actual = None
        self.page.update()

    def _confirmar_descartar(self, e=None):
        fila = self._fila_actual
        motivo = (self._campo_motivo.value or "").strip()
        if not motivo:
            self._mostrar_snack("El motivo es obligatorio.", error=True)
            return
        self._cerrar_dialogo_descartar()
        if not fila:
            return

        def _worker():
            res = VentasResolucionService.descartar(str(fila["id"]), motivo)
            self._mostrar_snack(res.get("message", ""), error=not res.get("success"))
            if res.get("success"):
                self._cargar_pendientes()

        threading.Thread(target=_worker, daemon=True).start()

    # --- Fusión ---
    def _abrir_dialogo_fusion(self, e=None):
        self._fusion_origen.value = ""
        self._fusion_destino.value = ""
        self._fusion_password.value = ""
        self._fusion_palabra.value = ""
        self._dialog_fusion.open = True
        self.page.update()

    def _cerrar_dialogo_fusion(self, e=None):
        self._dialog_fusion.open = False
        self.page.update()

    def _confirmar_fusion(self, e=None):
        origen = (self._fusion_origen.value or "").strip()
        destino = (self._fusion_destino.value or "").strip()
        password = self._fusion_password.value or ""
        palabra = self._fusion_palabra.value or ""
        self._cerrar_dialogo_fusion()

        def _worker():
            res = FusionProductoService.fusionar(
                producto_origen_id=origen,
                producto_destino_id=destino,
                password=password,
                palabra_confirmacion=palabra,
            )
            self._mostrar_snack(res.get("message", ""), error=not res.get("success"))
            if res.get("success"):
                self._cargar_pendientes()

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------
    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        if self.page:
            self.page.update()
