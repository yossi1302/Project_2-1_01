from __future__ import annotations

import asyncio
from pathlib import Path

import cv2
import flet as ft
import numpy as np

from .config import ExperimentConfig
from .live import LiveSnapshot, LiveTracker, ScreenGeometry
from .parallax import ParallaxRenderer

METHODS = ("mediapipe", "yunet", "haar")
DISPLAY_INTERVAL_S = 1.0 / 30.0
METRICS_INTERVAL_S = 0.2
SIDEBAR_WIDTH = 340

SURFACE = "#1a1a19"
PANEL = "#222220"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c3c2b7"
STATUS_GOOD = "#0ca30c"
STATUS_WARNING = "#fab219"
STATUS_CRITICAL = "#d03b3b"


def _blank_jpeg(width: int, height: int) -> bytes:
    _, encoded = cv2.imencode(".jpg", np.zeros((height, width, 3), dtype=np.uint8))
    return encoded.tobytes()


class StatTile(ft.Container):
    def __init__(self, label: str) -> None:
        self.value = ft.Text("--", size=20, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY)
        super().__init__(
            content=ft.Column(
                [ft.Text(label, size=12, color=TEXT_SECONDARY), self.value],
                spacing=2,
            ),
            bgcolor=PANEL,
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            expand=True,
        )

    def show(self, text: str) -> None:
        self.value.value = text


def run_gui(
    config: ExperimentConfig,
    model_directory: Path,
    calibration_path: Path,
    source: int | Path,
    method: str,
    screen: ScreenGeometry,
) -> None:
    tracker = LiveTracker(
        source=source,
        camera=config.camera,
        screen=screen,
        model_directory=model_directory,
        calibration_path=calibration_path,
        reference_distance_mm=config.calibration.reference_distance_mm,
        method=method,
    )
    tracker.open()
    renderer = ParallaxRenderer(lambda: tracker.snapshot().smoothed_position, screen)

    async def main(page: ft.Page) -> None:
        page.title = "Parallax viewer"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = SURFACE
        page.padding = 16
        page.window.width = 1360
        page.window.height = 940
        page.window.prevent_close = True

        scene = ft.Image(
            src=_blank_jpeg(16, 10),
            fit=ft.BoxFit.CONTAIN,
            gapless_playback=True,
            expand=True,
        )
        camera = ft.Image(
            src=_blank_jpeg(16, 9),
            fit=ft.BoxFit.CONTAIN,
            gapless_playback=True,
            border_radius=8,
            width=SIDEBAR_WIDTH,
            height=SIDEBAR_WIDTH * 9 / 16,
        )
        status_icon = ft.Icon(ft.Icons.HOURGLASS_TOP, color=STATUS_WARNING, size=18)
        status_text = ft.Text("Starting", color=TEXT_PRIMARY, size=14)

        tiles = {
            "x": StatTile("Eye x (right)"),
            "y": StatTile("Eye y (up)"),
            "z": StatTile("Distance"),
            "latency": StatTile("Tracking latency"),
            "camera_fps": StatTile("Camera rate"),
            "render_fps": StatTile("Render rate"),
            "detection": StatTile("Detection, last 60 frames"),
            "separation": StatTile("Eye separation"),
        }
        calibration_text = ft.Text("", size=12, color=TEXT_SECONDARY)

        def on_method(event: ft.Event[ft.Dropdown]) -> None:
            tracker.select_method(event.control.value)

        def on_gain(event: ft.Event[ft.Slider]) -> None:
            renderer.set_gain(float(event.control.value))

        def on_smoothing(event: ft.Event[ft.Switch]) -> None:
            tracker.set_smoothing(bool(event.control.value))

        def on_calibrate(_: ft.Event[ft.Button]) -> None:
            tracker.request_calibration()

        controls = ft.Column(
            [
                ft.Dropdown(
                    label="Tracking method",
                    value=method,
                    options=[ft.DropdownOption(key=name, text=name) for name in METHODS],
                    on_select=on_method,
                    width=SIDEBAR_WIDTH,
                ),
                ft.Text("Parallax gain", size=12, color=TEXT_SECONDARY),
                ft.Slider(
                    min=0.5,
                    max=2.0,
                    divisions=15,
                    value=1.0,
                    label="{value}x",
                    on_change=on_gain,
                ),
                ft.Switch(label="Smoothing (One Euro filter)", value=True, on_change=on_smoothing),
                ft.Button(
                    content=(
                        f"Calibrate at {tracker.reference_distance_mm:.0f} mm"
                    ),
                    icon=ft.Icons.CENTER_FOCUS_STRONG,
                    on_click=on_calibrate,
                ),
                calibration_text,
            ],
            spacing=8,
        )

        sidebar = ft.Container(
            width=SIDEBAR_WIDTH,
            content=ft.Column(
                [
                    camera,
                    ft.Row([status_icon, status_text], spacing=6),
                    ft.Row([tiles["x"], tiles["y"]]),
                    ft.Row([tiles["z"], tiles["separation"]]),
                    ft.Row([tiles["latency"], tiles["detection"]]),
                    ft.Row([tiles["camera_fps"], tiles["render_fps"]]),
                    ft.Divider(color=PANEL),
                    controls,
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
            ),
        )
        page.add(
            ft.Row(
                [
                    ft.Container(
                        content=scene,
                        expand=True,
                        bgcolor="#000000",
                        border_radius=8,
                        alignment=ft.Alignment.CENTER,
                    ),
                    sidebar,
                ],
                expand=True,
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )

        def show_metrics(snapshot: LiveSnapshot) -> None:
            position = snapshot.smoothed_position
            if position is not None:
                tiles["x"].show(f"{position.x_mm:+.0f} mm")
                tiles["y"].show(f"{position.y_mm:+.0f} mm")
                tiles["z"].show(f"{position.z_mm:.0f} mm")
            if snapshot.eyes is not None:
                tiles["separation"].show(f"{snapshot.eyes.separation_px:.1f} px")
            if snapshot.latency_ms is not None:
                tiles["latency"].show(f"{snapshot.latency_ms:.1f} ms")
            tiles["camera_fps"].show(f"{snapshot.camera_fps:.0f} fps")
            tiles["detection"].show(f"{snapshot.detection_rate_pct:.0f}%")
            frame = renderer.latest()
            if frame is not None:
                tiles["render_fps"].show(f"{frame.fps:.0f} fps")

            if renderer.error:
                icon, colour, text = ft.Icons.ERROR_OUTLINE, STATUS_CRITICAL, renderer.error
            elif snapshot.calibration_source == "measuring":
                icon, colour = ft.Icons.HOURGLASS_TOP, STATUS_WARNING
                text = f"Calibrating: hold still at {tracker.reference_distance_mm:.0f} mm"
            elif snapshot.detected:
                icon, colour, text = ft.Icons.CHECK_CIRCLE, STATUS_GOOD, snapshot.status
            else:
                icon, colour, text = ft.Icons.ERROR_OUTLINE, STATUS_CRITICAL, snapshot.status
            status_icon.icon = icon
            status_icon.color = colour
            status_text.value = text
            calibration_text.value = (
                f"Depth baseline: {snapshot.reference_eye_separation_px:.1f} px at "
                f"{tracker.reference_distance_mm:.0f} mm ({snapshot.calibration_source})"
            )

        async def refresh() -> None:
            scene_id = camera_id = -1
            loop = asyncio.get_running_loop()
            next_metrics = 0.0
            while True:
                snapshot = tracker.snapshot()
                frame = renderer.latest()
                changed = False
                if frame is not None and frame.frame_id != scene_id:
                    scene_id = frame.frame_id
                    scene.src = frame.jpeg
                    changed = True
                if snapshot.preview_jpeg is not None and snapshot.frame_id != camera_id:
                    camera_id = snapshot.frame_id
                    camera.src = snapshot.preview_jpeg
                    changed = True
                if loop.time() >= next_metrics:
                    next_metrics = loop.time() + METRICS_INTERVAL_S
                    show_metrics(snapshot)
                    changed = True
                if changed:
                    page.update()
                await asyncio.sleep(DISPLAY_INTERVAL_S)

        async def on_window_event(event: ft.WindowEvent) -> None:
            if event.type == ft.WindowEventType.CLOSE:
                renderer.stop()
                tracker.stop()
                await page.window.destroy()

        page.window.on_event = on_window_event
        page.update()
        await page.window.center()
        tracker.start()
        renderer.start()
        page.run_task(refresh)

    try:
        ft.run(main)
    finally:
        renderer.stop()
        tracker.stop()
