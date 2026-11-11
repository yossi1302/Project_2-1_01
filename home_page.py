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

def logo():
    city = ft.Text("City", font_family="Great Vibes", size=170, color=style.PRIMARY,
                   style=ft.TextStyle(height=1.0))
    flights = ft.Text("FLIGHTS", size=30, weight=ft.FontWeight.BOLD, color=style.ACCENT,
                      style=ft.TextStyle(letter_spacing=20))
    return ft.Column(
        spacing=0,
        tight=True,   # only as tall as the two words, so it can be centred
        controls=[
            city,
            # padding shifts FLIGHTS right, under the tail of "City"
            ft.Container(content=flights, padding=ft.Padding.only(left=150)),
        ],
    )

def square_button(icon, label, on_click=None):
    return ft.Column(
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                content=ft.Icon(icon, color=style.PRIMARY, size=30),
                width=64,
                height=64,
                alignment=ft.Alignment.CENTER,
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(1, style.LINE),
                border_radius=14,
                ink=True,
                on_click=on_click,
            ),
            ft.Text(label, size=13, color=style.INK),
        ],
    )

def try_out_card(on_start=None):
    return ft.Container(
        expand=True,
        padding=24,
        bgcolor=style.SOFT,
        border_radius=16,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text("TRY OUT", size=13, weight=ft.FontWeight.BOLD, color=style.ACCENT,
                        style=ft.TextStyle(letter_spacing=4)),
                ft.Text("Flying experience", size=28, color=style.INK),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Blink to fly to the next city", size=14, color=style.MUTED),
                        ft.Button(content="Start", icon=ft.Icons.SEND, bgcolor=style.PRIMARY,
                                color=ft.Colors.WHITE, on_click=on_start),
                    ],
                ),
            ],
        ),
    )

def build_home(cities, on_city, on_quit):
    city_buttons = [city_row(name, on_city) for name in cities]
    left=ft.Column(
        expand=True,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
                ft.Container(content=logo(), expand=True, alignment=ft.Alignment(-0.6, -0.5)),  # x, y from -1 (left/top) to 1 (right/bottom)
                ft.Container(
                    padding=ft.Padding.only(bottom=30),   # lifts the bottom buttons a little
                    content=ft.Row(
                        spacing=24,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            try_out_card(),
                            ft.Row(spacing=10, controls=[
                                square_button(ft.Icons.SETTINGS, "Settings"),
                                square_button(ft.Icons.DARK_MODE, "Night mode"),
                                square_button(ft.Icons.POWER_SETTINGS_NEW, "Quit", on_quit),
                            ]),
                        ],
                    ),
                ),
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
