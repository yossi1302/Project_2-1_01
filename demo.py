import time
import os
import asyncio
import psutil

import cv2
import numpy as np
import flet as ft

from render import Renderer, CITIES
from space import Eye, Screen
import space
import track
import style
from home_page import build_home

CAMERA_INDEX = 0     # cv2 device index; 0 is the OBS Virtual Camera on my mac (: - sean
IPD_CM = 6.3        # distance between the viewer's pupils; 6.3 is the adult average
FOCAL_PX = 1000     # camera focal length in pixels, for 1280x720 frames (estimate, not yet measured)
TRACK_WIDTH = 320   # frames are shrunk to this width before face detection (much faster)

# Convert eye positions in camera pixels to an Eye relative to the screen.
# The eye separation works as a ruler: IPD_CM / separation_px is cm per pixel
# at the viewer's distance, so x and z only depend on IPD_CM.
def eye_from_tracking(eyes, frame_w, frame_h, screen, focal_px=FOCAL_PX):
    cm_per_px = IPD_CM / eyes.separation_px
    mid = eyes.midpoint
    return Eye(
        x=-(mid.x - frame_w / 2) * cm_per_px,  # webcam image isn't mirrored
        y=focal_px * cm_per_px,
        z=screen.cam_offset - (mid.y - frame_h / 2) * cm_per_px,
    )

def main():
    rend = Renderer(frametime=1/30)

    async def gui_main(page):
        page.title = "City Flights"
        page.window.width = 1200
        page.window.height = 700
        page.padding = 0
        page.bgcolor = style.BG
        page.fonts = {"Great Vibes": "fonts/GreatVibes-Regular.ttf"}

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
        
        def go_home():
            rend.pause()
            city_view.visible=False
            home.visible=True
            page.update()

        async def quit_app():
            rend.stop()
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
            ],
            fit=ft.StackFit.EXPAND,
            expand=True,
            visible=False,
        )
                        
        home = build_home(CITIES, open_city, quit_app)
        page.add(
            home,
            city_view,
        )

        screen = Screen(width=40, height=17.5, cam_offset=0)
        # Latest tracked eye position.
        state = {"eye": Eye(x=0, y=25, z=10)}
        rend.configure_camera(space.place_camera(state["eye"], screen))

        async def monitor_memory():
            process = psutil.Process(os.getpid())

            while True:
                memory_mb = process.memory_info().rss / (1024 * 1024)

                print(f"Memory usage: {memory_mb:.1f} MB")

                await asyncio.sleep(5)

        async def track_viewer():
            cap = cv2.VideoCapture(CAMERA_INDEX)
            # Keep only the newest camera frame; a queue of old ones means lag.
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            tracker = track.Tracker()
            start, last_ts, last_preview = time.monotonic(), -1, 0.0
            try:
                while True:
                    # Nothing to track while the menu is showing.
                    if not city_view.visible:
                        await asyncio.sleep(0.1)
                        continue
                    # cap.read() waits for the next camera frame, which paces
                    # this loop at the camera's frame rate; no extra sleep.
                    ok, frame = await asyncio.to_thread(cap.read)
                    if not ok:
                        await asyncio.sleep(0.1)
                        continue
                    # VIDEO mode needs strictly increasing timestamps
                    last_ts = max(int((time.monotonic() - start) * 1000), last_ts + 1)

                    # Shrink for speed but keep the aspect ratio, so the pixel
                    # geometry (and therefore the distance estimate) stays right.
                    h, w = frame.shape[:2]
                    small = cv2.resize(frame, (TRACK_WIDTH, round(TRACK_WIDTH * h / w)),
                                       interpolation=cv2.INTER_AREA)
                    small_h, small_w = small.shape[:2]

                    result = await asyncio.to_thread(tracker.find, small, last_ts)
                    if result.detected:
                        # FOCAL_PX is for the full-size frame: scale it down too.
                        eye = eye_from_tracking(result.eyes, small_w, small_h, screen,
                                                focal_px=FOCAL_PX * small_w / w)
                        state["eye"] = eye
                        rend.configure_camera(space.place_camera(eye, screen))

                    # Camera preview, mirrored (tracking uses the unmirrored frame),
                    # at most 10 times per second: it is only a thumbnail.
                    now = time.monotonic()
                    if now - last_preview >= 0.1:
                        last_preview = now
                        preview = cv2.cvtColor(cv2.flip(small, 1), cv2.COLOR_BGR2RGBA)
                        try:
                            await camera_preview.render(preview, premultiplied=True)
                        except TimeoutError:
                            pass
            finally:
                cap.release()
                tracker.close()

        async def update_target():
            last_id = -1
            while True:
                #While the menu is showing, it skips the copying and just checks again in 0.1 s
                if not city_view.visible:
                    last_id = -1   # show the current frame again when coming back
                    await asyncio.sleep(0.1)
                    continue

                # Only a frame that is new, and of the right city, gets pushed.
                # The renderer already hands it over flipped and in RGBA, so
                # nothing is converted or copied here.
                item = rend.next_frame(last_id)
                if item is None:
                    await asyncio.sleep(0.004)
                    continue
                last_id, frame = item

                try:
                    # render() returns once Flet has displayed the frame, which
                    # naturally paces the loop to what the screen can take.
                    await target.render(frame, premultiplied=True)
                except TimeoutError:
                    continue

                if loading.visible:
                    loading.visible = False
                    page.update()

        page.update()
        await page.window.center()
        rend.run()
        page.run_task(update_target)
        page.run_task(track_viewer)
        page.run_task(monitor_memory)

    ft.run(gui_main)
    rend.stop()

if __name__ == "__main__":
    main()
