import flet as ft


def main(page: ft.page):
    page.title = "Productos"
    page.bgcolor ="#f5f6fa"
    page.padding = 20
    
    formulario = ft.Container(
        bgcolor="white",
        border_radius=15,
        expand=True,
        content=ft.Column(
            [
                 # Encabezado rojo
                 ft.Container(
                     bgcolor="#b40012",
                     padding= 20,
                     border_radius=ft.border_radius.only(
                         top_left=15,
                         top_right=15
                     ),
                     content=ft.row(
                         [
                             ft.Column(
                                 [
                                     ft.Text(
                                         "REGISTRAR PRODUCTO",
                                         color="white",
                                         weight=ft.FontWeight.BOLD,
                                         size=22,
                                     ),
                                     ft.tex(
                                         "Complete todos los campos obligatiorios(*)",
                                         color="white"
                                     ),
                                     
                                 ],
                               spacing=5  
                             ),
                             ft.Icon(
                                 ft.Icon.STAR,
                                 color="yellow",
                                 size=30
                             )
                         ],
                         alligament=ft.MainAxisAlignment.SPACE_BETWEEN
                     ),
                 ),
                 ft.Container(
                     padding=25,
                     content=ft.Column(
                         [
                             ft.Text(
                                 "Registrar Nuevo Producto",
                                 size=40,
                                 weight=ft.FontWeight.BOLD,
                             ),
                             ft.TextField(
                                 label="Nombre del producto *",
                                 hint_text="EJ: Agua de colonia",
                             ),
                             ft.Row(
                                 [
                                     ft.TextField(
                                         expand=True,
                                         laber="Código Único*",
                                         hint_text="EJ: RY-AUR-100",
                                     ),
                                     ft.dropdown(
                                         expand=True,
                                         label="Categoria",
                                         options=[
                                             ft.dropdown.Option("Perfumes"),
                                             ft.dropdown.Option("Envases"),
                                             ft.dropdown.Option("Accesorios"),
                                         ],
                                     ),
                                 ]
                             ),
                             ft.TextField(
                                 label="Precio de Costo*",
                                 prefix_text="$",
                             ),
                             ft.Row(
                                 [
                                     ft.TextField(
                                         expand=True,
                                         label="Cantidad Inicial",
                                         value=0,
                                     ),
                                     ft.RadioGroup(
                                         content=ft.Row(
                                             [
                                                 ft.Text("Unidad"),
                                                 ft.Radio(value="u", label="u"),
                                                 ft.Radio(value="gr", label="gr"),
                                             ]
                                         ),
                                         value="u",
                                     ),
                                 ]
                             ),
                             ft.Row(
                                 [
                                     ft.OutlinedBorder(
                                         "CANCELAR/ VOLVER",
                                         expand=True,
                                         heigh=50,
                                     ),
                                     ft.FilledButton(
                                         "GUARDAR PRODUCTO",
                                         expand=True,
                                         heigh=50,
                                         style=ft.ButtonStyle(
                                             bgcolor="#b40012",
                                             color="white",
                                         ),
                                     ),
                                 ]
                             )
                         ],
                         spacing=20,
                     )
                 ),
            ],
            spacing=0,
        ),
    )
    
    panel_derecho = ft.Column(
        [
            ft.Container(
                 bgcolor="white",
                border_radius=15,
                padding=20,
                height=170,
                content=ft.Column(
                    [
                        ft.Text(
                            "Mensajes de Validación",
                            weight=ft.FontWeight.BOLD,
                            size=18,
                        ),
                        ft.Text(
                            "Aquí aparecerán errores o confirmaciones después de intentar guardar el producto.",
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
                    [
                        ft.Text(
                            "Registro Reciente",
                            weight=ft.FontWeight.BOLD,
                            size=18,
                        ),

                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.CARD_GIFT_CARD),
                            title=ft.Text("Kit Envasado"),
                            subtitle=ft.Text("Código: RY-ACC-021"),
                        ),

                        ft.Divider(),

                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.SCIENCE),
                            title=ft.Text("Fragancia Citrus 1kg"),
                            subtitle=ft.Text("Código: RY-MP-012"),
                        ),

                        ft.Divider(),

                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.LOCAL_DRINK),
                            title=ft.Text("Envase PET 250ml"),
                            subtitle=ft.Text("Código: RY-ENV-007"),
                        ),
                    ]
                ),
            ),
        ],
        width=400,
        spacing=20,
    )

    page.add(
        ft.Column(
            [
                ft.Text(
                    "Productos",
                    size=28,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text(
                    "Gestión de productos en inventario",
                    color="grey",
                ),

                ft.Row(
                    [
                        formulario,
                        panel_derecho,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ]
        )
    )

ft.app(target=main)
            
        
    

