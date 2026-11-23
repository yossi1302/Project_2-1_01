import gc
import threading
import time

from direct.showbase.ShowBase import ShowBase
from panda3d.core import Texture, FrameBufferProperties, WindowProperties, GraphicsPipe, GraphicsOutput, PerspectiveLens
from panda3d.core import LColorf, Point3, RenderState, TransformState, TexturePool, ModelPool

import math

import numpy as np

import space
from cities import paris, new_york, venice

CITY = "new_york"  # Pick starting scene (not relevant cause not displayed)

CITIES = {
    "paris": paris.load_paris,
    "new_york": new_york.load_new_york,
    "venice": venice.load_venice,
}

# Merge the static city geometry into a handful of big meshes once it is loaded
# (Paris: ~520 separate draw calls per frame -> 3). Looks identical; set to
# False to compare the "Panda3D sans capture" timings in the console.
FLATTEN_SCENE = True

# Street-level placement for cities that define a SPAWN.
SPAWNS = {
    "paris": paris.SPAWN,
    "new_york": new_york.SPAWN,
    "venice": venice.SPAWN,
}
CITY_SCALE = 10          # cm on the screen side per city unit
EYE_HEIGHT = 1.6         # viewer's eye height above the city ground, in city units
CITY_GROUND_Z = -1.0     # ground level used by the city files
VIEWER_DISTANCE = 50     # typical eye distance from the screen, in cm

# Scale and turn the city so the spawn point sits where the viewer's eyes are:
# straight out from the screen centre, VIEWER_DISTANCE cm away, facing look_at.
def place_viewer(scene, spawn):
    x, y = spawn["position"]
    tx, ty = spawn["look_at"]
    heading = math.degrees(math.atan2(tx - x, ty - y))
    scene.setPos(0, 0, 0)
    scene.setHpr(heading, 0, 0)
    scene.setScale(CITY_SCALE)
    eye = scene.getParent().getRelativePoint(scene, Point3(x, y, CITY_GROUND_Z + EYE_HEIGHT))
    scene.setPos(Point3(0, -VIEWER_DISTANCE, 0) - eye)

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

        # The last frame is always stored here after being rendered, already
        # converted to what Flet wants: top-down RGBA, alpha = 255.
        # Two buffers are reused forever (no allocation per frame): the render
        # thread fills the spare one, then swaps it in under render_lock.
        self.frame_array = np.full((1, 1, 4), 255, dtype=np.uint8)
        self._spare_frame = np.full((1, 1, 4), 255, dtype=np.uint8)
        self.frame_id = 0   # incremented for every frame stored

        self.view_mode = "parallax"  # "editor" for a fixed 45-degree view and "parallax" for eye-tracking view
        self.camera_config = None

        self.requested_city = CITY
        self.active = threading.Event()   # set = drawing, cleared = paused
        self.frame_city = None   
        
    def run(self):
        self.thread.start()

    def stop(self):
        self.stop_requested.set()
        if self.thread.is_alive():
            self.active.set()
            self.thread.join(timeout=3)

    def pause(self):
            self.active.clear()
    
    def resume(self):
        self.active.set()

    # Returns the last rendered frame as a numpy uint8 array (H, W, 4), RGBA, top-down.
    def last_frame(self):
        with self.render_lock:
            return self.frame_array

    # Returns (frame_id, frame) if a frame of the requested city that is newer
    # than `last_id` is available, otherwise None. Lets the GUI push each
    # frame exactly once, and never a frame of the previous city.
    def next_frame(self, last_id):
        with self.render_lock:
            if self.frame_city != self.requested_city or self.frame_id == last_id:
                return None
            return self.frame_id, self.frame_array

    def configure_camera(self, config):
        self.camera_config = config

    def set_city(self, name):
        if name in CITIES:
            self.requested_city=name
        else:
            raise ValueError('City not in the catalogue')

    def frame_is_current(self):
        with self.render_lock:
            return self.frame_city == self.requested_city


    def thread_proc(self):
        base = ShowBase(
            fStartDirect=True,
            windowType="offscreen",
        )
        base.disableMouse()

        # ShowBase also opens a default offscreen window that uses the same
        # camera as ours, so every frame was being rendered twice (the second
        # copy was never read). Switch that one off.
        base.win.setActive(False)

        fb_prop = FrameBufferProperties()
        fb_prop.setRgbColor(True)
        fb_prop.setRgbaBits(8, 8, 8, 0)
        fb_prop.setDepthBits(24)

        win_prop = WindowProperties.size(800, 450)

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
            GraphicsOutput.RTMCopyRam,
            GraphicsOutput.RTPColor
        )
        disp_region = window.makeDisplayRegion()
        disp_region.setCamera(base.cam)
        disp_region.setClearColorActive(True)
        disp_region.setClearColor(LColorf(0.72, 0.82, 0.88, 1))

        lens = PerspectiveLens()
        lens.setNearFar(1, 5000)  # scaled cities reach several metres deep
        base.cam.node().setLens(lens)

        #makes the city display a node of its own
        scene = base.render.attachNewNode("Scene")
        current_city = None
        last_log = time.perf_counter()

        while not self.stop_requested.is_set():
            self.active.wait()
            if self.stop_requested.is_set():
                break
            requested_city = self.requested_city
            if requested_city != current_city:
                scene.removeNode()
                self.free_unused_memory()
                scene = base.render.attachNewNode("Scene")
                #looks into the dictionary for the right function
                load_city = CITIES[requested_city]
                load_city(scene, base.loader)
                if FLATTEN_SCENE:
                    scene.flattenStrong()
                if self.view_mode == "parallax" and requested_city in SPAWNS:
                    place_viewer(scene, SPAWNS[requested_city])
                gc.collect()   # the glTF loader leaves reference cycles behind
                current_city = requested_city

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

            start = time.perf_counter()

            base.graphicsEngine.renderFrame()
            self.record_frame(render_tex, current_city)

            render_ms = (time.perf_counter() - start) * 1000

            if time.perf_counter() - last_log >= 5:
                print(f"Panda3D sans capture : {render_ms:.1f} ms")
                last_log = time.perf_counter()

            # If the frame finished early
            # (which should be most of the time)
            # then wait the rest of the allotted period.
            elapsed = time.perf_counter() - start_time
            wait_time = self.frametime - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
        base.destroy()

    # Panda3D and the glTF loader keep a lot of garbage alive after a city is
    # removed (Python reference cycles, pooled textures/models, cached render
    # states). Without this, memory grew by several MB on every city change.
    def free_unused_memory(self):
        gc.collect()
        RenderState.garbageCollect()
        TransformState.garbageCollect()
        TexturePool.releaseAllTextures()
        ModelPool.releaseAllModels()

    def record_frame(self, tex, city):
        h, w, c = tex.getYSize(), tex.getXSize(), tex.getNumComponents()
        if tex.getRamImageSize() == 0:
            return   # nothing copied back from the GPU yet

        # Panda3D gives bottom-up BGR(A); Flet wants top-down RGBA. The flip and
        # the channel swap are done here, on the render thread, straight into
        # a reused buffer instead of allocating several new arrays per frame on
        # the GUI thread.
        src = np.frombuffer(tex.getRamImage(), dtype=np.uint8).reshape(h, w, c)[::-1]

        out = self._spare_frame
        if out.shape[:2] != (h, w):
            out = np.full((h, w, 4), 255, dtype=np.uint8)
        out[..., 0] = src[..., 2]
        out[..., 1] = src[..., 1]
        out[..., 2] = src[..., 0]

        with self.render_lock:
            self._spare_frame = self.frame_array
            self.frame_array = out
            self.frame_city = city
            self.frame_id += 1
