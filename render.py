import threading
import time

from direct.showbase.ShowBase import ShowBase
from panda3d.core import Texture, FrameBufferProperties, WindowProperties, GraphicsPipe, GraphicsOutput

import numpy as np

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
        self.frame_array = np.empty((1, 1), dtype=np.uint8)

    def run(self):
        self.thread.start()

    def stop(self):
        self.stop_requested.set()
        if self.thread.is_alive():
            self.thread.join(timeout=3)

    # Returns the last rendered frame as a numpy uint8 array
    def last_frame(self):
        return self.frame_array

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
        disp_region = window.makeDisplayRegion()

        # This texture is where the actual offscreen window contents will go.
        render_tex = Texture()
        window.addRenderTexture(
            render_tex,
            GraphicsOutput.RTMCopyRam, GraphicsOutput.RTPColor
        )

        while not self.stop_requested.is_set():
            start_time = time.perf_counter()

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
        self.frame_array = np.frombuffer(img, dtype=np.uint8)
        self.frame_array.shape = (
            tex.getYSize(), tex.getXSize(), tex.getNumComponents()
        )

