"""
Vista de la pantalla principal del dashboard.

Muestra tarjetas de resumen y opciones de navegación
después de un inicio de sesión exitoso.
El diseño se adapta según el rol del usuario (administrador / vendedor).

Parámetros:
    rol       (str)      : Rol del usuario, usado para mostrar u ocultar
                        funciones de administrador.
    on_logout (callable) : Se llama (sin argumentos) cuando el usuario
                        hace clic en 'Cerrar Sesión'.

Retorna:
    ft.Container: El layout completo del dashboard, listo para agregar a la página.

Reglas:
    - SIN lógica de negocio — solo diseño e interfaz condicional.
    - Los widgets de tarjetas se importan desde src/ui/components/cards.py.
    - SIN acceso al objeto `page` — se comunica solo mediante callbacks.
"""

import flet as ft




# =====================================================
# BOTONES DEL SIDEBAR
# =====================================================
# Esta función crea cada botón del menú izquierdo
#
# icon       -> icono
# text       -> texto visible
# page_name  -> nombre interno de la página
# on_click   -> función que cambia el contenido
# =====================================================
def sidebar_item(icon, text, page_name, on_click):

    return ft.Container(

        padding=10,

        border_radius=10,

        # =================================================
        # EVENTO CLICK
        # =================================================
        on_click=lambda e: on_click(page_name),

        content=ft.Row(
            controls=[

                ft.Icon(
                    icon,
                    color="white",
                    size=20,
                ),

                ft.Text(
                    text,
                    color="white",
                    size=14,
                ),
            ]
        ),
    )


# =====================================================
# VISTA PRINCIPAL
# =====================================================
def DashboardView(rol: str, on_logout):

    # =================================================
    # AREA DINAMICA DERECHA
    # =================================================
    # Aquí aparecerá:
    # - dashboard
    # - productos
    # - ventas
    # =================================================
    content_area = ft.Column(
        expand=True,
        spacing=20,
    )

    # =================================================
    # FUNCION PARA CAMBIAR CONTENIDO
    # =================================================
    def load_content(page_name):

        # =============================================
        # LIMPIAR CONTENIDO ANTERIOR
        # =============================================
        content_area.controls.clear()

        # =============================================
        # DASHBOARD
        # =============================================
        if page_name == "dashboard":

            content_area.controls.extend([

                ft.Text(
                    "DASHBOARD",
                    size=30,
                    weight="bold",
                    color="black",
                ),

                ft.Text(
                    "PANEL PRINCIPAL",
                    color="gray",
                    size=14,
                ),

                # =====================================
                # CARDS
                # =====================================
                ft.Row(
                    spacing=20,
                    controls=[

                        # CARD 1
                        ft.Container(
                            expand=True,
                            bgcolor="white",
                            padding=20,
                            border_radius=15,

                            content=ft.Column(
                                controls=[

                                    ft.Text(
                                        "PRODUCTOS",
                                        size=12,
                                        color="gray",
                                        weight="bold",
                                    ),

                                    ft.Text(
                                        "0",
                                        size=30,
                                        weight="bold",
                                    ),

                                    ft.Text(
                                        "Total inventario",
                                        color="gray",
                                    ),
                                ]
                            ),
                        ),

                        # CARD 2
                        ft.Container(
                            expand=True,
                            bgcolor="white",
                            padding=20,
                            border_radius=15,

                            content=ft.Column(
                                controls=[

                                    ft.Text(
                                        "VENTAS",
                                        size=12,
                                        color="gray",
                                        weight="bold",
                                    ),

                                    ft.Text(
                                        "$0",
                                        size=30,
                                        weight="bold",
                                    ),

                                    ft.Text(
                                        "Ventas hoy",
                                        color="gray",
                                    ),
                                ]
                            ),
                        ),
                    ],
                ),
            ])

        # =============================================
        # PRODUCTOS
        # =============================================
        elif page_name == "PRODUCTOS":

            content_area.controls.extend([

                ft.Text(
                    "PRODUCTOS",
                    size=30,
                    weight="bold",
                ),

                ft.Text(
                    "Aquí irán los productos",
                    color="gray",
                ),
            ])

        # =============================================
        # VENTAS
        # =============================================
        elif page_name == "VENTAS":

            content_area.controls.extend([

                ft.Text(
                    "VENTAS",
                    size=30,
                    weight="bold",
                ),

                ft.Text(
                    "Aquí irán las ventas",
                    color="gray",
                ),
            ])

        # =============================================
        # BODEGAS
        # =============================================
        elif page_name == "BODEGAS":

            content_area.controls.extend([

                ft.Text(
                    "BODEGAS",
                    size=30,
                    weight="bold",
                ),

                ft.Text(
                    "Aquí irán las bodegas",
                    color="gray",
                ),
            ])

        # =============================================
        # ACTUALIZAR INTERFAZ
        # =============================================
        content_area.update()

    # =================================================
    # CARGAR DASHBOARD AL INICIAR
    # =================================================
    load_content("dashboard")

    # =================================================
    # SIDEBAR IZQUIERDO
    # =================================================
    sidebar = ft.Container(

        width=220,

        bgcolor="#b3001b",

        padding=20,

        content=ft.Column(

            expand=True,

            spacing=20,

            controls=[

                # =====================================
                # LOGO / TITULO
                # =====================================
                ft.Column(
                    spacing=5,
                    controls=[

                        ft.Text(
                            "👑 REY",
                            size=24,
                            weight="bold",
                            color="white",
                        ),

                        ft.Text(
                            "Inventarios",
                            color="white70",
                            size=12,
                        ),
                    ],
                ),

                ft.Divider(color="white24"),

                # =====================================
                # MENU
                # =====================================

                sidebar_item(
                    ft.Icons.DASHBOARD,
                    "Dashboard",
                    "dashboard",
                    load_content,
                ),

                sidebar_item(
                    ft.Icons.WAREHOUSE,
                    "Bodegas",
                    "BODEGAS",
                    load_content,
                ),

                sidebar_item(
                    ft.Icons.INVENTORY_2,
                    "Productos",
                    "PRODUCTOS",
                    load_content,
                ),

                sidebar_item(
                    ft.Icons.SWAP_HORIZ,
                    "Movimientos",
                    "MOVIMIENTOS",
                    load_content,
                ),

                sidebar_item(
                    ft.Icons.SHOPPING_CART,
                    "Ventas",
                    "VENTAS",
                    load_content,
                ),

                sidebar_item(
                    ft.Icons.PEOPLE,
                    "Clientes",
                    "CLIENTES",
                    load_content,
                ),

                sidebar_item(
                    ft.Icons.BAR_CHART,
                    "Reportes",
                    "REPORTES",
                    load_content,
                ),

                sidebar_item(
                    ft.Icons.DESCRIPTION,
                    "Bitácora",
                    "BITACORA",
                    load_content,
                ),

                # =====================================
                # EMPUJAR BOTON HACIA ABAJO
                # =====================================
                ft.Container(expand=True),

                # =====================================
                # BOTON LOGOUT
                # =====================================
                ft.ElevatedButton(
                    "Cerrar sesión",
                    icon=ft.Icons.LOGOUT,
                    width=180,
                    bgcolor="#8b0015",
                    color="white",
                    on_click=lambda _: on_logout(),
                ),
            ],
        ),
    )

    # =================================================
    # CONTENIDO DERECHO
    # =================================================
    content = ft.Container(

        expand=True,

        padding=20,

        bgcolor="#F5F5F5",

        # =============================================
        # AREA DINAMICA
        # =============================================
        content=content_area,
    )

    # =================================================
    # RETORNO FINAL
    # =================================================
    return ft.Row(

        expand=True,

        spacing=0,

        controls=[
            sidebar,
            content,
        ],
    )
        