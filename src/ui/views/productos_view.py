"""
Vista de Productos.

Permite registrar nuevos productos y visualizar los registros recientes.
Sigue el mismo patrón que bodegas_view.py:
  - Función pública ProductosView() que envuelve la clase privada.
  - Clase _ProductosView hereda de ft.Container.
  - Todas las llamadas al servicio corren en hilos de fondo (threading).
  - Dialog y SnackBar se registran en page.overlay desde did_mount().

Reglas:
    - SIN lógica de negocio — solo diseño e interacción de interfaz.
    - SIN llamadas directas a Supabase.
    - SIN ft.app() — esta vista es montada por dashboard_view.py.
"""

import threading
import flet as ft
from src.services.productos_service import ProductosService
from src.services.bodegas_service import BodegasService


def ProductosView():
    return ft.Column(controls=[_ProductosView()])


class _ProductosView(ft.Container):

    def __init__(self):
        super().__init__()
        self.expand = True
        self.bgcolor = "#f5f6fa"
        self.padding = 20

        self._bodegas: list[dict] = []
        self._productos_recientes: list[dict] = []

        self._campo_nombre = ft.TextField(
            label="Nombre del producto *",
            hint_text="Ej: Agua de colonia",
            border_radius=10,
        )
        self._campo_tipo = ft.TextField(
            label="Tipo / Categoría *",
            hint_text="Ej: Perfume, Envase, Insumo",
            expand=True,
            border_radius=10,
        )
        self._campo_funcion = ft.TextField(
            label="Función *",
            hint_text="Ej: Venta directa, Empaque",
            expand=True,
            border_radius=10,
        )
        self._campo_stock = ft.TextField(
            label="Cantidad Inicial",
            value="0",
            expand=True,
            border_radius=10,
        )
        self._campo_unidad = ft.RadioGroup(
            content=ft.Row(
                controls=[
                    ft.Text("Unidad de medida:"),
                    ft.Radio(value="u", label="u"),
                    ft.Radio(value="gr", label="gr"),
                ]
            ),
            value="u",
        )
        self._campo_bodega = ft.Dropdown(  # ✅ Dropdown (mayúscula)
            label="Bodega *",
            expand=True,
            border_radius=10,
            options=[],
        )

        
        self._lista_recientes = ft.Column(
            spacing=0,
            controls=[ft.Text("Cargando...", color="grey", italic=True)],
        )

      
        self._snackbar = ft.SnackBar(content=ft.Text(""), show_close_icon=True)

        self.content = ft.Column(
            spacing=0,
            controls=[
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text(
                            "Productos",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="#222",
                        ),
                        ft.Text(
                            "Gestión de productos en inventario",
                            size=12,
                            color="grey",
                        ),
                    ],
                ),
                ft.Container(height=20),
                ft.Row(
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        self._formulario(),
                        self._panel_derecho(),
                    ],
                ),
            ],
        )

  

    def did_mount(self):
        """
        Registra el snackbar en page.overlay (una sola vez)
        y arranca la carga inicial en un hilo de fondo.
        """
        self.page.overlay.append(self._snackbar)
        self.page.update()
        threading.Thread(target=self._cargar_datos_iniciales, daemon=True).start()


    def _cargar_datos_iniciales(self):
        """
        Carga las bodegas para el dropdown y los últimos 5 productos
        para el panel de registros recientes.
        """
        # Bodegas → para el dropdown
        res_bodegas = BodegasService.get_all()
        if res_bodegas["success"]:
            self._bodegas = res_bodegas["data"]
            self._campo_bodega.options = [
                ft.DropdownOption(key=b["id"], text=b["nombre"])  
                for b in self._bodegas
            ]

  
        res_productos = ProductosService.get_all()
        if res_productos["success"]:
            self._productos_recientes = res_productos["data"][:5]
            self._refrescar_lista_recientes()

        self.page.update()

    def _refrescar_lista_recientes(self):
        self._lista_recientes.controls.clear()

        if not self._productos_recientes:
            self._lista_recientes.controls.append(
                ft.Text("No hay productos registrados aún.", color="grey", italic=True)
            )
            return

        for p in self._productos_recientes:
            self._lista_recientes.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.INVENTORY_2, color="#b40012"),
                    title=ft.Text(p.get("nombre", "—")),
                    subtitle=ft.Text(p.get("tipo", "—")),
                )
            )
            self._lista_recientes.controls.append(ft.Divider())

    ─

    def _formulario(self):
        return ft.Container(
            bgcolor="white",
            border_radius=15,
            expand=True,
            content=ft.Column(
                spacing=0,
                controls=[
                   
                    ft.Container(
                        bgcolor="#b40012",
                        padding=20,
                        border_radius=ft.border_radius.only(top_left=15, top_right=15),
                        content=ft.Row(  
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,  
                                ft.Column(
                                    spacing=5,
                                    controls=[
                                        ft.Text(  
                                            "REGISTRAR PRODUCTO",
                                            color="white",
                                            weight=ft.FontWeight.BOLD,
                                            size=22,
                                        ),
                                        ft.Text( 
                                            "Complete todos los campos obligatorios (*)",
                                            color="white",
                                        ),
                                    ],
                                ),
                                ft.Icon(
                                    ft.Icons.STAR,  
                                    color="yellow",
                                    size=30,
                                ),
                            ],
                        ),
                    ),
                    
                    ft.Container(
                        padding=25,
                        content=ft.Column(
                            spacing=20,
                            controls=[
                                self._campo_nombre,
                                ft.Row(
                                    controls=[
                                        self._campo_tipo,
                                        self._campo_funcion,
                                    ]
                                ),
                                ft.Row(
                                    controls=[
                                        self._campo_stock,
                                        self._campo_unidad,
                                    ]
                                ),
                                self._campo_bodega,
                                ft.Row(
                                    controls=[
                                        ft.OutlinedButton( 
                                            "CANCELAR / VOLVER",
                                            expand=True,
                                            height=50, 
                                            on_click=self._limpiar_formulario,
                                        ),
                                        ft.FilledButton(
                                            "GUARDAR PRODUCTO",
                                            expand=True,
                                            height=50, 
                                            style=ft.ButtonStyle(
                                                bgcolor="#b40012",
                                                color="white",
                                            ),
                                            on_click=self._guardar_producto,
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )

    

    def _panel_derecho(self):
        return ft.Column(
            width=400,
            spacing=20,
            controls=[
                ft.Container(
                    bgcolor="white",
                    border_radius=15,
                    padding=20,
                    height=170,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Mensajes de Validación",
                                weight=ft.FontWeight.BOLD,
                                size=18,
                            ),
                            ft.Text(
                                "Aquí aparecerán errores o confirmaciones "
                                "después de intentar guardar el producto.",
                                italic=True,
                                color="grey",
                            ),
                        ]
                    ),
                ),
                ft.Container(
                    bgcolor="white",
                    border_radius=15,
                    padding=20,
                    expand=True,
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Registros Recientes",
                                weight=ft.FontWeight.BOLD,
                                size=18,
                            ),
                            self._lista_recientes,
                        ]
                    ),
                ),
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Acciones
    # ─────────────────────────────────────────────────────────────────────────

    def _guardar_producto(self, e):
        nombre = self._campo_nombre.value.strip()
        tipo = self._campo_tipo.value.strip()
        funcion = self._campo_funcion.value.strip()
        unidad = self._campo_unidad.value
        bodega_id = self._campo_bodega.value

        try:
            stock = int(self._campo_stock.value or 0)
        except ValueError:
            self._mostrar_snack("⚠️ La cantidad debe ser un número entero.", error=True)
            self.page.update()
            return

        if not nombre or not tipo or not funcion or not bodega_id:
            self._mostrar_snack(
                "⚠️ Completa todos los campos obligatorios (*).", error=True
            )
            self.page.update()
            return

        def _worker():
            result = ProductosService.create(
                nombre=nombre,
                tipo=tipo,
                funcion=funcion,
                unidad_medida=unidad,
                stock=stock,
                bodega_id=bodega_id,
            )
            self._mostrar_snack(result["message"], error=not result["success"])
            if result["success"]:
                self._limpiar_formulario()
                self._cargar_datos_iniciales() 

        threading.Thread(target=_worker, daemon=True).start()

    def _limpiar_formulario(self, e=None):
        self._campo_nombre.value = ""
        self._campo_tipo.value = ""
        self._campo_funcion.value = ""
        self._campo_stock.value = "0"
        self._campo_unidad.value = "u"
        self._campo_bodega.value = None
        self.page.update()


    def _mostrar_snack(self, mensaje: str, error: bool = False):
        self._snackbar.content = ft.Text(mensaje, color="white")
        self._snackbar.bgcolor = "#d32f2f" if error else "#388e3c"
        self._snackbar.open = True
        self.page.update()
