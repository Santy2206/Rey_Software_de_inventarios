import flet as ft


def dashboard_card(titulo, numero, subtitulo):
    
    return ft.Container(
        width="300",
        height="130",
        
        bgcolor="white",
        
        border_radius=15,
        
        padding=20,
        
        content=ft.Column(
            
            spacing=10,
            
            controls=[
                
                ft.Text(
                    titulo,
                    size=14,
                    weight="bold",
                    color="#666666"
                    
                ),
                ft.Text(
                    numero,
                    size=15,
                    weight="bold",
                    color="#111111"
                ),
                ft.Text(
                    subtitulo,
                    size=12,
                    color="#999999"
                )
            ]
        )
        
    )
    return ft.Container(
        
        expand=True,
        
        bgcolor="#f5f5f5",
        
        padding=20,
        
        content=ft.Column(
            
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    
                    controls=[
                        
                        ft.Text(
                            "Dashboard",
                            size=30,
                            weight="bold"
                        ),
                        ft.Text(
                            "Panel Principal",
                            Color="gray"
                        )
                    ]
                ),
                ft.Container(
                    bgcolor="white",
                    
                    padding=10,
                    
                    border_radius=30,
                    
                    content=ft.Text(
                        "🟢 Online",
                        color="green"
                    )
                )
            ]
        )
    ),
    
        
    