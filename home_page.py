import flet as ft

import style


def city_row(name, on_city):
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(name.replace("_", " ").title(), size=18, color=style.INK),
                ft.Icon(ft.Icons.SEND, color=style.ACCENT, size=20),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, style.LINE),
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=18, vertical=12),
        ink=True,
        on_click=lambda e: on_city(name),
    )

def build_home(cities, on_city, on_quit):
    city_buttons = [city_row(name, on_city) for name in cities]
    left=ft.Column(
        expand=True,
        controls=[
                ft.Text("City Flights", size=40, color=style.PRIMARY),
                ft.Button(content="Quit", on_click=on_quit),
        ]
    )
    right=ft.Column(
                width=420,
                spacing=10,
                controls=[
                    ft.Text("CITIES", size=18, weight=ft.FontWeight.BOLD, color=style.PRIMARY,style=ft.TextStyle(letter_spacing=4)),
                ]+ city_buttons,
            )
    return ft.Container(
        expand=True,
        padding=40,
        bgcolor=style.BG,
        content=ft.Row(controls=[left, right], spacing=40),
    )
