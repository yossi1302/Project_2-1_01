import time
import os
import asyncio

import cv2
import numpy as np
import flet as ft

from render import Renderer

def main():
    rend = Renderer(frametime=1/60)

    async def gui_main(page):
        page.title = "Eye tracking demo"
        page.window.width = 1200
        page.window.height = 700

        # Image where the render texture will get copied.
        target = ft.Image(
            src=encode_frame(rend.last_frame()),
            fit=ft.BoxFit.CONTAIN,
            gapless_playback=True,
            expand=True,
        )
        page.add(target)

        async def update_target():
            while True:
                last = rend.last_frame()
                target.src = encode_frame(last)
                page.update()
                await asyncio.sleep(1/60)

        page.update()
        rend.run()
        page.run_task(update_target)

    ft.run(gui_main)

def encode_frame(frame):
    ok, encoded = cv2.imencode(
        ".jpg", np.flipud(frame), [cv2.IMWRITE_JPEG_QUALITY, 85]
    )
    if not ok:
        os.exit(1)
    return encoded.tobytes()

if __name__ == "__main__":
    main()

