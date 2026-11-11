import time
import asyncio
import logging
import math

import cv2
import numpy as np
import flet as ft

from render import Renderer
from space import Eye, Screen
from metrics import TrackingMetrics
import space
import track

CAMERA_INDEX = 1     # cv2 device index; 0 is the OBS Virtual Camera on my mac (: - sean
IPD_CM = 6.3        # distance between the viewer's pupils; 6.3 is the adult average
FOCAL_PX = 1000     # camera focal length in pixels, for 1280x720 frames (estimate, not yet measured)

# Convert eye positions in camera pixels to an Eye relative to the screen.
# The eye separation works as a ruler: IPD_CM / separation_px is cm per pixel
# at the viewer's distance, so x and z only depend on IPD_CM.
def eye_from_tracking(eyes, frame_w, frame_h, screen):
    if eyes is None or not math.isfinite(eyes.separation_px) or eyes.separation_px <= 0:
        return None
    cm_per_px = IPD_CM / eyes.separation_px
    mid = eyes.midpoint
    eye = Eye(
        x=-(mid.x - frame_w / 2) * cm_per_px,  # webcam image isn't mirrored
        y=FOCAL_PX * cm_per_px,
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
        self.status = ft.Text("Waiting for camera", color="#FBBF24", size=14)
        self.summary = ft.Text(color="#CBD5E1", size=12)
        self.values = ft.Text(color="#FFFFFF", size=13)
        self.position = ft.Text(color="#FFFFFF", size=13)
        self.control = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Eye tracking", color="#FFFFFF", size=16,
                            weight=ft.FontWeight.BOLD),
                    self.status,
                    self.summary,
                    self.values,
                    self.position,
                    ft.Text(
                        "Position is estimated from assumed eye spacing and camera focal length.",
                        color="#94A3B8", size=11,
                    ),
                ],
                spacing=6,
                tight=True,
            ),
            width=310, left=12, top=12, padding=14,
            bgcolor="#E6101827", border_radius=8,
        )

    def refresh(self, snapshot):
        def milliseconds(value):
            return "—" if value is None else f"{value:.1f} ms"

        detection = "—" if snapshot.detection_pct is None else f"{snapshot.detection_pct:.1f}%"
        age = "Never" if snapshot.last_seen_seconds is None else f"{snapshot.last_seen_seconds:.1f} s ago"
        self.status.value = snapshot.status
        self.status.color = "#4ADE80" if snapshot.status == "Eyes detected" else "#FBBF24"
        self.summary.value = f"Last 5 s · {snapshot.samples} processed frames"
        self.values.value = (
            f"Tracking FPS: {snapshot.fps:.1f}\n"
            f"Detection: {detection} ({snapshot.detected}/{snapshot.samples})\n"
            f"Tracker latency · median: {milliseconds(snapshot.median_ms)}\n"
            f"Tracker latency · P95: {milliseconds(snapshot.p95_ms)}\n"
            f"Last detected: {age}"
        )
        if snapshot.position_cm is None:
            self.position.value = "Estimated position: —\nEye separation: —"
        else:
            x, distance, z = snapshot.position_cm
            self.position.value = (
                f"Estimated position (cm)\n"
                f"Horizontal: {x:+.1f} · Vertical: {z:+.1f}\n"
                f"Distance from screen: {distance:.1f}\n"
                f"Eye separation: {snapshot.separation_px:.1f} px"
            )

def main():
    rend = Renderer(frametime=1/60)

    async def gui_main(page):
        page.title = "Eye tracking demo"
        page.window.width = 1200
        page.window.height = 700
        metrics = TrackingMetrics(time.monotonic())
        panel = MetricsPanel()
        panel.refresh(metrics.snapshot(time.monotonic()))

        # Image where the render texture will get copied.
        target = ft.RawImage(fit=ft.BoxFit.CONTAIN, expand=True)
        camera_preview = ft.RawImage(fit=ft.BoxFit.CONTAIN)
        page.add(
            ft.Stack(
                controls=[
                    target,
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
                    panel.control,
                ],
                fit=ft.StackFit.EXPAND,
                expand=True,
            )
        )

        screen = Screen(width=40, height=17.5, cam_offset=0)
        # Keep the scene at the last known position if tracking drops out.
        state = {"eye": Eye(x=0, y=25, z=10), "running": True}

        async def track_viewer():
            cap = tracker = None
            try:
                cap = await asyncio.to_thread(cv2.VideoCapture, CAMERA_INDEX)
                if not cap.isOpened():
                    metrics.unavailable("Camera unavailable")
                    return
                tracker = await asyncio.to_thread(track.Tracker)
                start, last_ts = time.monotonic(), -1
                while state["running"]:
                    ok, frame = await asyncio.to_thread(cap.read)
                    if not ok:
                        metrics.unavailable("Camera frame unavailable")
                        await asyncio.sleep(0.1)
                        continue
                    # VIDEO mode needs strictly increasing timestamps.
                    last_ts = max(int((time.monotonic() - start) * 1000), last_ts + 1)
                    result, latency_ms = await asyncio.to_thread(
                        timed_tracking, tracker, frame, last_ts
                    )
                    completed_at = time.monotonic()
                    h, w = frame.shape[:2]
                    eye = eye_from_tracking(result.eyes, w, h, screen) if result.detected else None
                    metrics.record(
                        completed_at, latency_ms,
                        position_cm=(eye.x, eye.y, eye.z) if eye else None,
                        separation_px=result.eyes.separation_px if eye else None,
                    )
                    if eye:
                        state["eye"] = eye
                    if not state["running"]:
                        break

                    # Mirror only the preview; track the original frame.
                    scale = min(240 / w, 135 / h)
                    preview = cv2.resize(frame, (max(1, round(w * scale)), max(1, round(h * scale))))
                    preview = cv2.cvtColor(cv2.flip(preview, 1), cv2.COLOR_BGR2RGB)
                    await camera_preview.render(preview)
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
            while state["running"]:
                config = space.place_camera(state["eye"], screen)
                rend.configure_camera(config)

                # The frame is flipped since panda3d and flet
                # don't agree on vertical orientation.
                await target.render(np.flip(rend.last_frame(), 0))
                await asyncio.sleep(1/60)

        page.update()
        page.on_disconnect = disconnect
        rend.configure_camera(space.place_camera(state["eye"], screen))
        rend.run()
        page.run_task(update_target)
        page.run_task(track_viewer)
        page.run_task(update_metrics)

    ft.run(gui_main)

if __name__ == "__main__":
    main()
