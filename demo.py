import time
import os
import psutil
import asyncio
import logging
import math
import random as rand

import cv2
import flet as ft

from render import Renderer, CITIES
from space import Eye, Screen
from metrics import TrackingMetrics
import space
import track
import style
from home_page import build_home

CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", 1))  # cv2 device index; on my mac 0 = OBS Virtual Camera, 1 = FaceTime HD - sean
IPD_CM = 6.3        # distance between the viewer's pupils; 6.3 is the adult average
FOCAL_PX = 1000     # camera focal length in pixels, for 1280x720 frames (estimate, not yet measured)
TRACK_WIDTH = 320

# Convert eye positions in camera pixels to an Eye relative to the screen.
# The eye separation works as a ruler: IPD_CM / separation_px is cm per pixel
# at the viewer's distance, so x and z only depend on IPD_CM.
def eye_from_tracking(eyes, frame_w, frame_h, screen, focal_px=FOCAL_PX):
    if eyes is None or not math.isfinite(eyes.separation_px) or eyes.separation_px <= 0:
        return None
    cm_per_px = IPD_CM / eyes.separation_px
    mid = eyes.midpoint
    eye = Eye(
        x=-(mid.x - frame_w / 2) * cm_per_px,  # webcam image isn't mirrored
        y=focal_px * cm_per_px,
        z=screen.cam_offset - (mid.y - frame_h / 2) * cm_per_px,
    )
    return eye if all(math.isfinite(value) for value in (eye.x, eye.y, eye.z)) else None


def timed_tracking(tracker, frame, timestamp):
    # Time the call here so waiting for a worker doesn't inflate the latency.
    started = time.perf_counter()
    result = tracker.find(frame, timestamp)
    return result, (time.perf_counter() - started) * 1000.0


class MetricsPanel:
    def __init__(self):
        self.status = ft.Text("Waiting for camera", color=style.MUTED, size=12,
                              expand=True)
        self.status_dot = ft.Container(width=7, height=7, border_radius=4,
                                       bgcolor=style.ACCENT)
        self.summary = ft.Text(color=style.MUTED, size=11)
        self.fps = ft.Text("—", color=style.PRIMARY, size=26, weight=ft.FontWeight.W_600)
        self.detection = ft.Text("—", color=style.PRIMARY, size=26,
                                 weight=ft.FontWeight.W_600)
        self.detection_count = ft.Text("0/0 frames", color=style.MUTED, size=11)

        def stat_card(label, value, detail):
            return ft.Container(
                expand=True, bgcolor=style.SOFT, border_radius=12, padding=12,
                content=ft.Column(spacing=2, tight=True, controls=[
                    ft.Text(label, color=style.MUTED, size=11), value, detail,
                ]),
            )

        def metric_row(label, value):
            return ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[ft.Text(label, color=style.MUTED, size=12), value],
            )

        def value_text():
            return ft.Text("—", color=style.INK, size=12, weight=ft.FontWeight.W_600)

        def section_title(label):
            return ft.Text(label, color=style.PRIMARY, size=11,
                           weight=ft.FontWeight.BOLD,
                           style=ft.TextStyle(letter_spacing=1.2))

        self.median = value_text()
        self.p95 = value_text()
        self.last_seen = value_text()
        self.horizontal = value_text()
        self.vertical = value_text()
        self.distance = value_text()
        self.separation = value_text()
        self.control = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(spacing=10, controls=[
                        ft.Container(
                            content=ft.Icon(ft.Icons.VISIBILITY_OUTLINED,
                                            color=style.PRIMARY, size=20),
                            bgcolor=style.SOFT, border_radius=10,
                            width=36, height=36, alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column(spacing=2, tight=True, controls=[
                            ft.Text("Eye tracking", color=style.INK, size=17,
                                    weight=ft.FontWeight.W_600),
                            self.summary,
                        ]),
                    ]),
                    ft.Row(spacing=7, controls=[self.status_dot, self.status]),
                    ft.Row(spacing=8, controls=[
                        stat_card("Tracking FPS", self.fps,
                                  ft.Text("frames / second", color=style.MUTED, size=11)),
                        stat_card("Detection", self.detection, self.detection_count),
                    ]),
                    ft.Column(spacing=7, tight=True, controls=[
                        section_title("TRACKER LATENCY"),
                        metric_row("Median", self.median),
                        metric_row("P95", self.p95),
                        metric_row("Last detected", self.last_seen),
                    ]),
                    ft.Divider(height=1, thickness=1, color=style.LINE),
                    ft.Column(spacing=7, tight=True, controls=[
                        section_title("ESTIMATED POSITION"),
                        metric_row("Horizontal", self.horizontal),
                        metric_row("Vertical", self.vertical),
                        metric_row("Distance from screen", self.distance),
                        metric_row("Eye separation", self.separation),
                    ]),
                    ft.Text(
                        "Position is estimated from assumed eye spacing and camera focal length.",
                        color=style.MUTED, size=11,
                    ),
                    ft.TextButton(
                        content=ft.Text("What do these metrics mean?", color=style.PRIMARY,
                                        size=12),
                        on_click=self.show_help,
                        style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=0, vertical=4)),
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            width=320, left=16, top=12, padding=16,
            bgcolor=ft.Colors.WHITE, border_radius=16,
            border=ft.Border.all(1, style.LINE),
        )

    def show_help(self, event):
        page = event.control.page
        explanations = [
            ("Tracking status",
             "Shows whether the latest frame produced a valid eye position. "
             "Camera and tracking errors appear here too. If no new result arrives "
             "for a second, the position is hidden until tracking resumes."),
            ("Last 5 s / processed frames",
             "The statistics use a moving five-second window. Processed frames "
             "counts frames analysed by the tracker, including frames where no eyes "
             "were found. When the app first starts, the window is shorter."),
            ("Tracking FPS",
             "Frames analysed per second. Higher values mean more frequent tracking "
             "updates. This includes unsuccessful detections and is separate from "
             "the scene's rendering FPS."),
            ("Detection",
             "The percentage of processed frames with a valid eye pair and position. "
             "For example, 90% (90/100) means 90 of 100 frames succeeded. "
             "It measures how often tracking works, not how accurate the position is. "
             "Camera-read failures are shown as errors and are not counted as detector calls."),
            ("Tracker latency · median",
             "The middle tracking-call duration: about half the calls finish faster "
             "and half slower. Lower is better. Timing includes image conversion and "
             "eye detection, but excludes camera capture, waiting for a worker, "
             "rendering, and display updates. One millisecond (ms) is 1/1,000 of a second."),
            ("Tracker latency · P95",
             "About 95% of tracking calls finish within this time; the slowest 5% "
             "may take longer. For example, P95 = 20 ms means about 95 out of 100 "
             "calls finish within 20 ms. Lower is better. This helps reveal slower "
             "updates that the median can hide, but it is not the maximum delay. "
             "Both latency statistics include calls where no eyes were detected."),
            ("Last detected",
             "Time since the tracker last returned a valid eye position. It grows "
             "when tracking is lost. Never means no valid position has been found "
             "since the app started. The scene holds its last known viewpoint during a loss."),
            ("Horizontal / vertical position",
             "The estimated eye midpoint relative to the screen centre, in centimetres "
             "(cm). Horizontal is the side-to-side offset; vertical is the height. "
             "The signs show the direction along the app's coordinate axes, "
             "and zero is the centre."),
            ("Distance from screen",
             "Estimated distance straight out from the screen plane to the eye "
             "midpoint, in centimetres. It changes as you lean towards or away "
             "from the screen."),
            ("Eye separation",
             "Distance between the two detected eye centres in the camera image, "
             "in pixels (px). It usually becomes smaller as you move away. "
             "Head rotation can change it too. It is not the physical distance "
             "between your eyes."),
            ("Estimated values and dashes",
             "Position uses an assumed eye spacing of 6.3 cm and an estimated "
             "camera focal length. Treat it as approximate, especially when turning "
             "your head. A dash means no current measurement is available; it "
             "does not mean zero."),
        ]
        sections = []
        for title, explanation in explanations:
            sections.append(ft.Text(title, weight=ft.FontWeight.BOLD, size=14, color=style.PRIMARY))
            sections.append(ft.Text(explanation, size=13, color=style.INK))
        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Eye-tracking metrics explained", color=style.INK),
            bgcolor=style.BG,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Column(controls=sections, width=460, spacing=8, tight=True),
            scrollable=True,
            actions=[ft.TextButton("Close", style=ft.ButtonStyle(color=style.PRIMARY),
                                   on_click=lambda _: page.pop_dialog())],
        ))

    def refresh(self, snapshot):
        def milliseconds(value):
            return "—" if value is None else f"{value:.1f} ms"

        detection = "—" if snapshot.detection_pct is None else f"{snapshot.detection_pct:.1f}%"
        age = "Never" if snapshot.last_seen_seconds is None else f"{snapshot.last_seen_seconds:.1f} s ago"
        self.status.value = snapshot.status
        self.status.color = style.PRIMARY if snapshot.status == "Eyes detected" else style.MUTED
        self.status_dot.bgcolor = style.PRIMARY if snapshot.status == "Eyes detected" else style.ACCENT
        self.summary.value = f"Last 5 s · {snapshot.samples} processed frames"
        self.fps.value = f"{snapshot.fps:.1f}"
        self.detection.value = detection
        self.detection_count.value = f"{snapshot.detected}/{snapshot.samples} frames"
        self.median.value = milliseconds(snapshot.median_ms)
        self.p95.value = milliseconds(snapshot.p95_ms)
        self.last_seen.value = age
        if snapshot.position_cm is None:
            for value in (self.horizontal, self.vertical, self.distance, self.separation):
                value.value = "—"
        else:
            x, distance, z = snapshot.position_cm
            self.horizontal.value = f"{x:+.1f} cm"
            self.vertical.value = f"{z:+.1f} cm"
            self.distance.value = f"{distance:.1f} cm"
            self.separation.value = f"{snapshot.separation_px:.1f} px"


def main():
    rend = Renderer(frametime=1/30)

    async def gui_main(page):
        page.title = "City Flights"
        page.window.width = 1200
        page.window.height = 700
        page.padding = 0
        page.bgcolor = style.BG
        page.fonts = {"Great Vibes": "fonts/GreatVibes-Regular.ttf"}
        metrics = TrackingMetrics(time.monotonic())
        panel = MetricsPanel()
        panel.control.top = 76  # Leave room for the Menu button.
        panel.refresh(metrics.snapshot(time.monotonic()))

        # Image where the render texture will get copied.
        target = ft.RawImage(fit=ft.BoxFit.CONTAIN, expand=True)
        camera_preview = ft.RawImage(fit=ft.BoxFit.CONTAIN)

        def open_city(name):
            rend.set_city(name)
            rend.resume()
            home.visible=False
            city_view.visible=True
            loading.visible = True
            page.update()

        def go_home(_event=None):
            rend.pause()
            city_view.visible=False
            home.visible=True
            state["flying"] = False
            page.update()

        def fly():
            others = [name for name in CITIES if name != rend.requested_city]
            open_city(rand.choice(others))

        def start_flying(_event=None):
            state["flying"] = True
            fly()

        async def quit_app(_event=None):
            state["running"] = False
            await asyncio.to_thread(rend.stop)
            await page.window.close()


        city_view=ft.Stack(
            controls=[
                target,
                loading := ft.Container(
                    expand=True,
                    bgcolor=style.BG,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("Loading…", size=20, color=style.PRIMARY),
                    visible=False,
                ),
                ft.Container(
                    content=camera_preview,
                    width=240,
                    height=135,
                    top=12,
                    right=12,
                    bgcolor=ft.Colors.BLACK,
                    border_radius=8,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
                ft.Container(
                    content=ft.Row(
                        tight=True,
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.ARROW_BACK, color=style.PRIMARY, size=20),
                            ft.Text("Menu", size=16, color=style.INK),
                        ],
                    ),
                    top=16,
                    left=16,
                    bgcolor=ft.Colors.WHITE,
                    border=ft.Border.all(1, style.LINE),
                    border_radius=10,
                    padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                    ink=True,
                    on_click=go_home,
                ),
                panel.control,
            ],
            fit=ft.StackFit.EXPAND,
            expand=True,
            visible=False,
        )

        home = build_home(CITIES, open_city, quit_app, start_flying)
        page.add(
            home,
            city_view,
        )

        screen = Screen(width=40, height=17.5, cam_offset=0)
        # Keep the scene at the last known position if tracking drops out.
        state = {"eye": Eye(x=0, y=25, z=10), "running": True ,"flying": False}
        eye_filter = space.EyeFilter()

        async def monitor_memory():
            process = psutil.Process(os.getpid())
            while state["running"]:
                print(f"Memory usage: {process.memory_info().rss / (1024 * 1024):.1f} MB")
                await asyncio.sleep(5)

        async def track_viewer():
            cap = tracker = None
            try:
                cap = await asyncio.to_thread(cv2.VideoCapture, CAMERA_INDEX)
                blinks = track.BlinkDetector()
                if not cap.isOpened():
                    metrics.unavailable("Camera unavailable")
                    return
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                tracker = await asyncio.to_thread(track.Tracker)
                start, last_ts, last_preview = time.monotonic(), -1, 0.0
                while state["running"]:
                    if not city_view.visible:
                        await asyncio.sleep(0.1)
                        continue
                    ok, frame = await asyncio.to_thread(cap.read)
                    if not ok:
                        metrics.unavailable("Camera frame unavailable")
                        await asyncio.sleep(0.1)
                        continue
                    h, w = frame.shape[:2]
                    if not w or not h:
                        continue
                    small = cv2.resize(frame, (TRACK_WIDTH, max(1, round(TRACK_WIDTH * h / w))),
                                       interpolation=cv2.INTER_AREA)
                    small_h, small_w = small.shape[:2]
                    last_ts = max(int((time.monotonic() - start) * 1000), last_ts + 1)
                    result, latency_ms = await asyncio.to_thread(
                        timed_tracking, tracker, small, last_ts
                    )
                    completed_at = time.monotonic()
                    if blinks.update(result.blink, last_ts) and state["flying"]:
                        fly()
                    eye = (eye_from_tracking(result.eyes, small_w, small_h, screen,
                                             focal_px=FOCAL_PX * small_w / w)
                           if result.detected else None)
                    metrics.record(
                        completed_at, latency_ms,
                        position_cm=(eye.x, eye.y, eye.z) if eye else None,
                        separation_px=result.eyes.separation_px if eye else None,
                    )
                    if eye:
                        state["eye"] = eye_filter(eye, completed_at)
                        rend.configure_camera(space.place_camera(state["eye"], screen))
                    if not state["running"]:
                        break
                    if completed_at - last_preview >= 0.1:
                        last_preview = completed_at
                        preview = cv2.cvtColor(cv2.flip(small, 1), cv2.COLOR_BGR2RGBA)
                        try:
                            await camera_preview.render(preview, premultiplied=True)
                        except TimeoutError:
                            pass
            except Exception:
                logging.exception("Eye tracking stopped")
                metrics.unavailable("Tracking error — see terminal")
            finally:
                if cap is not None:
                    cap.release()
                if tracker is not None:
                    tracker.close()

        async def update_metrics():
            while state["running"]:
                panel.refresh(metrics.snapshot(time.monotonic()))
                panel.control.update()
                await asyncio.sleep(0.2)

        async def disconnect(_event):
            state["running"] = False
            await asyncio.to_thread(rend.stop)

        async def update_target():
            last_id = -1
            while state["running"]:
                if not city_view.visible:
                    last_id = -1
                    await asyncio.sleep(0.1)
                    continue
                item = rend.next_frame(last_id)
                if item is None:
                    await asyncio.sleep(0.004)
                    continue
                last_id, frame = item
                try:
                    await target.render(frame, premultiplied=True)
                except TimeoutError:
                    continue
                if loading.visible:
                    loading.visible = False
                    page.update()

        page.update()
        page.on_disconnect = disconnect
        rend.configure_camera(space.place_camera(state["eye"], screen))
        await page.window.center()
        rend.run()
        page.run_task(update_target)
        page.run_task(track_viewer)
        page.run_task(update_metrics)
        page.run_task(monitor_memory)

    ft.run(gui_main)
    rend.stop()

if __name__ == "__main__":
    main()
