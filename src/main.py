import flet as ft

def main(page: ft.Page):
    
    #------------------Configuración de ventana---------------------

    page.title = "REY Inventarios"

    page.window_width = 1200
    page.window_height = 700

    page.bgcolor = "#b3001b"
    
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    
    
    
    
    #-------------------Login Usuario--------------------------------

    login_card = ft.Container(
        width=350,
        
        height=420,
        
        bgcolor="#c1273d",
        
        border_radius=20,
        
        padding=30,
        
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                #------Corona--------------------
                ft.Text("👑",
                        size=40
                        
                    
                ),
                #---------------Titulo--------------------
                ft.Text(
                    "REY",
                    
                    size=40,
                    
                    weight="bold",
                    
                    color="white",
                    
                #----------------Subtitulo----------------- 
                ),
                ft.Text(
                    "SOFTWARE DE INVENTARIOS",
                    
                    size=12,
                    
                    weight="bold",
                    
                    color="white"
                ),
                #----------------Usuario--------------------
                
                ft.TextField(
                    hint_text="Usuario",
                    
                    border_radius=30,
                    
                    filled=True,
                    
                    bgcolor="#f5e6d3",
                    
                    border_color="transparent"
                ),
                #--------------Contraseña--------------------
                
                ft.TextField(
                    hint_text="Contraseña",
                    
                    password=True,
                    
                    can_reveal_password=True,
                    
                    border_radius=30,
                    
                    filled=True,
                    
                    bgcolor="#f5e6d3",
                    
                    border_color="transparent"
                    
                ),
                #----------Espacio------------------
                
                ft.Container(height=10),
                
                #------Boton--------
                
                ft.ElevatedButton(
                    "INGRESAR",
                    
                    width=250,
                    
                    height=50,
                    
                    bgcolor="#f2c500",
                    
                    color="black",
                    
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=30)
                    )
                ),
                #----------------Espacio--------------------
                ft.Container(height=5),
                
                #-----------------Footer------------
                ft.Text(
                    "v2.0 © 2026 REY Inventarios",
                    size=10,
                    height=520,
                    color="#ffb3b3"
                )
            ]
        )
    )
    
    

    page.add(
        ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                 login_card
            ]
           
            )
        )
    page.vertical_alignment= ft.MainAxisAlignment.CENTER
        
        
        
        
    
ft.app(target=main)