import time
import os
import asyncio

import cv2
import numpy as np
import flet as ft

from render import Renderer
from space import Eye, Screen
import space
import track

CAMERA_INDEX = 1     # cv2 device index; 0 is the OBS Virtual Camera on my mac (: - sean
IPD_CM = 6.3        # distance between the viewer's pupils; 6.3 is the adult average
FOCAL_PX = 1000     # camera focal length in pixels, for 1280x720 frames (estimate, not yet measured)

# Convert eye positions in camera pixels to an Eye relative to the screen.
# The eye separation works as a ruler: IPD_CM / separation_px is cm per pixel
# at the viewer's distance, so x and z only depend on IPD_CM.
def eye_from_tracking(eyes, frame_w, frame_h, screen):
    cm_per_px = IPD_CM / eyes.separation_px
    mid = eyes.midpoint
    return Eye(
        x=-(mid.x - frame_w / 2) * cm_per_px,  # webcam image isn't mirrored
        y=FOCAL_PX * cm_per_px,
        z=screen.cam_offset - (mid.y - frame_h / 2) * cm_per_px,
    )

def main():
    rend = Renderer(frametime=1/60)

    async def gui_main(page):
        page.title = "Eye tracking demo"
        page.window.width = 1200
        page.window.height = 700

        # Image where the render texture will get copied.
        target = ft.RawImage(fit=ft.BoxFit.CONTAIN, expand=True)
        page.add(target)

        screen = Screen(width=40, height=17.5, cam_offset=0)
        # Latest tracked eye position, shared between the two tasks.
        state = {"eye": Eye(x=0, y=25, z=10)}

        async def track_viewer():
            cap = cv2.VideoCapture(CAMERA_INDEX)
            tracker = track.Tracker()
            start, last_ts = time.monotonic(), -1
            while True:
                ok, frame = await asyncio.to_thread(cap.read)
                if not ok:
                    await asyncio.sleep(0.1)
                    continue
                # VIDEO mode needs strictly increasing timestamps
                last_ts = max(int((time.monotonic() - start) * 1000), last_ts + 1)
                result = await asyncio.to_thread(tracker.find, frame, last_ts)
                if result.detected:
                    h, w = frame.shape[:2]
                    state["eye"] = eye_from_tracking(result.eyes, w, h, screen)

        async def update_target():
            while True:
                config = space.place_camera(state["eye"], screen)
                rend.configure_camera(config)

                # The frame is flipped since panda3d and flet
                # don't agree on vertical orientation.
                await target.render(np.flip(rend.last_frame(), 0))
                await asyncio.sleep(1/60)

        page.update()
        rend.run()
        page.run_task(update_target)
        page.run_task(track_viewer)

    ft.run(gui_main)

if __name__ == "__main__":
    main()
