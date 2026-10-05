import time
import os
import asyncio

import cv2
import numpy as np
import flet as ft

from render import Renderer
from space import Eye, Screen
import space

def main():
    rend = Renderer(frametime=1/60)

    async def gui_main(page):
        page.title = "Eye tracking demo"
        page.window.width = 1200
        page.window.height = 700

        # Image where the render texture will get copied.
        target = ft.RawImage(fit=ft.BoxFit.CONTAIN, expand=True)
        page.add(target)

        async def update_target():
            eye = Eye(x=0, y=25, z=10)
            screen = Screen(width=40, height=17.5, cam_offset=0)

            while True:
                eye.x += 0.03
                config = space.place_camera(eye, screen)
                rend.configure_camera(config)

                # The frame is flipped since panda3d and flet
                # don't agree on vertical orientation.
                await target.render(np.flip(rend.last_frame(), 0))
                await asyncio.sleep(1/60)

        page.update()
        rend.run()
        page.run_task(update_target)

    ft.run(gui_main)

if __name__ == "__main__":
    main()

