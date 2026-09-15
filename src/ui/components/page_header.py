"""
Header de página con dashboard de estado separado.

Divide la cabecera en dos niveles:
  1. Título/subtítulo a la izquierda; estado de sincronización + usuario a la derecha.
  2. Botones de acción (crear, importar, etc.) alineados a la derecha, debajo del panel de estado.
"""

import flet as ft


def PageHeader(
    title: str,
    subtitle: str,
    status_control,
    action_buttons=None,
):
    """
    Construye el header de una vista.

    Args:
        title: Nombre del panel actual (ej: "Productos").
        subtitle: Descripción corta del panel.
        status_control: Control con estado de sincronización y usuario
                        (por ejemplo, StatusHeader.control).
        action_buttons: Lista opcional de botones de acción que se mostrarán
                        en una segunda fila, debajo del dashboard de estado.
    """
    secciones = [
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            title,
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="#222222",
                        ),
                        ft.Text(
                            subtitle,
                            size=12,
                            color="#666666",
                        ),
                    ],
                ),
                status_control,
            ],
        ),
    ]

    if action_buttons:
        secciones.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.END,
                spacing=10,
                controls=action_buttons,
            )
        )

    return ft.Column(spacing=10, controls=secciones)
