from email.mime import base
import threading
import time

from direct.showbase.ShowBase import ShowBase
from panda3d.core import Texture, FrameBufferProperties, WindowProperties, GraphicsPipe, GraphicsOutput, PerspectiveLens
from panda3d.core import LColorf

import numpy as np

import space
from cities import paris, new_york

CITY = "paris"  # Change to "new_york" to switch scenes

# Panda3d-backed renderer which draws to a texture
# instead of a window.
# This is where the actual scene will be rendered,
# then passed on to some frontend to be copied to the screen.
class Renderer:
    def __init__(self, *, frametime):
        self.frametime = frametime  # Target frame time, in seconds

        # Renderer runs on this thread;
        # it will continuously push out frames and is protected by render_lock.
        self.thread = threading.Thread(
            target=self.thread_proc,
            name="render",
            daemon=True
        )
        self.render_lock = threading.Lock()

        # Set this flag to ask the render thread to finish
        self.stop_requested = threading.Event()

        # This is where the last frame is always stored
        # after being rendered.
        self.frame_array = np.empty((1, 1, 3), dtype=np.uint8)

        self.view_mode = "editor"  # "editor" for a fixed 45-degree view and "parallax" for eye-tracking view
        self.camera_config = None

    def run(self):
        self.thread.start()

    def stop(self):
        self.stop_requested.set()
        if self.thread.is_alive():
            self.thread.join(timeout=3)

    # Returns the last rendered frame as a numpy uint8 array
    def last_frame(self):
        with self.render_lock:
            return self.frame_array

    def configure_camera(self, config):
        self.camera_config = config

    def thread_proc(self):
        base = ShowBase(
            fStartDirect=True,
            windowType="offscreen",
        )
        base.disableMouse()

        fb_prop = FrameBufferProperties()
        fb_prop.setRgbColor(True)
        fb_prop.setRgbaBits(8, 8, 8, 0)
        fb_prop.setDepthBits(24)

        win_prop = WindowProperties.size(1200, 700)

        # Create an offscreen window to render to.
        window = base.graphicsEngine.makeOutput(
            base.pipe, "cameraview", 0,
            fb_prop, win_prop,
            GraphicsPipe.BFRefuseWindow
        )

        # This texture is where the actual offscreen window contents will go.
        render_tex = Texture()
        window.addRenderTexture(
            render_tex,
            GraphicsOutput.RTMCopyRam, GraphicsOutput.RTPColor
        )
        disp_region = window.makeDisplayRegion()
        disp_region.setCamera(base.cam)
        disp_region.setClearColorActive(True)
        disp_region.setClearColor(LColorf(0.72, 0.82, 0.88, 1))

        lens = PerspectiveLens()
        lens.setNearFar(1, 500)
        base.cam.node().setLens(lens)

        if CITY == "paris":
            paris.load_paris(base.render, base.loader)
        elif CITY == "new_york":
            new_york.load_new_york(base.render, base.loader)
        else:
            raise ValueError(f"Unknown city: {CITY}")

        while not self.stop_requested.is_set():
            start_time = time.perf_counter()
                
            if self.view_mode == "editor":
                base.cam.setPos(45, -45, 55)
                base.cam.lookAt(0, 10, 0)

                lens.setFilmOffset(0, 0)
                lens.setFilmSize(60, 35)
                lens.setFocalLength(80)

            elif self.camera_config is not None:
                cfg = self.camera_config

                base.cam.setPos(*cfg.pos)
                base.cam.setHpr(0, 0, 0)

                lens.setFilmSize(cfg.film_size)
                lens.setFilmOffset(cfg.film_offset)
                lens.setFocalLength(cfg.focal_length)

            base.graphicsEngine.renderFrame()
            self.record_frame(render_tex)

            # If the frame finished early
            # (which should be most of the time)
            # then wait the rest of the allotted period.
            elapsed = time.perf_counter() - start_time
            wait_time = self.frametime - elapsed
            if wait_time > 0:
                time.sleep(wait_time)

    def record_frame(self, tex):
        img = tex.getRamImage()

        with self.render_lock:
            self.frame_array = np.frombuffer(img, dtype=np.uint8)
            self.frame_array.shape = (
                tex.getYSize(), tex.getXSize(), tex.getNumComponents()
            )

