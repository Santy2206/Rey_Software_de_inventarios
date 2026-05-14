import flet as ft
import psycopg2
from views.dashboard import dashboard_card

#conexion = psycopg2.connect(
    #host="localhost",
    #database="Rey_Inventarios",
    #user="postgres",
    #password="Admin123"

#)

#cursor = conexion.cursor()


def main(page: ft.Page):

    #------------------Configuración de ventana---------------------

    page.title = "REY Inventarios"

    page.window_width = 1200
    page.window_height = 700

    page.bgcolor = "#b3001b"

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    #----------------------Text Fields----------------------
    
    
    
    usuario_input = ft.TextField(
        hint_text="Usuario",
        border_radius=30,
        filled=True,
        bgcolor="#f5e6d3",
        border_color="transparent",
        cursor_color="black",
        color="black"
        
    )

    password_input = ft.TextField(
        hint_text="Contraseña",
        password=True,
        can_reveal_password=True,
        border_radius=30,
        filled=True,
        bgcolor="#f5e6d3",
        border_color="transparent",
        cursor_color="black",
        color="black"
    )
    
    #------------------Validar Login----------------------------
    
   # def validar_login(e):
        
       # usuario = usuario_input.value
        #contraeña = password_input.value
        
        #cursor.execute(
            #"SELECT * FROM usuarios WHERE usuario=%s AND contraseña=%s",
            #(usuario, contraseña)
        #)

        #resultado = cursor.fetchone()

        #if resultado:

            #page.snack_bar = ft.SnackBar(
                #ft.Text("Bienvenido al sistema")
            #)

        #else:

            #page.snack_bar = ft.SnackBar(
            #    ft.Text("Usuario o contraseña incorrectos")
            #)

        #page.snack_bar.open = True
        #page.update()
   

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
                ft.Text("👑", size=40),

                ft.Text(
                    "REY",
                    size=40,
                    weight="bold",
                    color="white",
                ),

                ft.Text(
                    "SOFTWARE DE INVENTARIOS",
                    size=12,
                    weight="bold",
                    color="white"
                ),
                usuario_input,

                password_input,

                ft.Container(height=10),

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

                ft.Container(height=5),

                ft.Text(
                    "v2.0 © 2026 REY Inventarios",
                    size=10,
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
    


ft.app(target=main, view=ft.AppView.WEB_BROWSER)

