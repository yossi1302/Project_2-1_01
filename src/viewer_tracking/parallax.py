from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

import cv2
import numpy as np

from .live import EyePosition, ScreenGeometry

# Panda3D scene units are centimetres. Its axes are x right, y into the screen, z up.
MM_PER_UNIT = 10.0
ROOM_DEPTH_CM = 45.0
MIN_EYE_DISTANCE_MM = 150.0
DEFAULT_EYE = EyePosition(0.0, 0.0, 600.0)

BACKGROUND = (0.102, 0.102, 0.098, 1.0)
GRID_COLOUR = (0.224, 0.529, 0.898, 1.0)
WALL_COLOUR = (0.13, 0.13, 0.125, 1.0)


@dataclass(frozen=True)
class OffAxisView:
    """Camera placement and asymmetric frustum that treat the screen as a window."""

    camera_position: tuple[float, float, float]
    film_size: tuple[float, float]
    film_offset: tuple[float, float]
    focal_length: float


def off_axis_view(eye: EyePosition, screen: ScreenGeometry, gain: float = 1.0) -> OffAxisView:
    """Place the virtual camera at the viewer's eye and aim its frustum at the screen edges.

    The screen occupies the plane y = 0, centred on the origin. `gain` scales the
    viewer's sideways and vertical motion to exaggerate or calm the effect.
    """
    x = gain * eye.x_mm / MM_PER_UNIT
    z = gain * eye.y_mm / MM_PER_UNIT
    distance = max(eye.z_mm, MIN_EYE_DISTANCE_MM) / MM_PER_UNIT
    return OffAxisView(
        camera_position=(x, -distance, z),
        film_size=(screen.width_mm / MM_PER_UNIT, screen.height_mm / MM_PER_UNIT),
        # With the focal length equal to the distance to the screen, film units match
        # scene units on the screen plane, so the offset is the screen centre seen from the eye.
        film_offset=(-x, -z),
        focal_length=distance,
    )


@dataclass(frozen=True)
class RenderedFrame:
    jpeg: bytes
    frame_id: int
    render_ms: float
    fps: float


class ParallaxRenderer:
    """Renders the Panda3D room offscreen on a worker thread and keeps the latest frame."""

    def __init__(
        self,
        eye_source: Callable[[], EyePosition | None],
        screen: ScreenGeometry,
        width_px: int = 1280,
        target_fps: float = 60.0,
    ) -> None:
        self._eye_source = eye_source
        self._screen = screen
        self._width_px = width_px
        self._height_px = round(width_px * screen.height_mm / screen.width_mm)
        self._frame_interval_s = 1.0 / target_fps
        self._gain = 1.0
        self._frame: RenderedFrame | None = None
        self._error: str | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="parallax-renderer", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def set_gain(self, gain: float) -> None:
        with self._lock:
            self._gain = gain

    def latest(self) -> RenderedFrame | None:
        with self._lock:
            return self._frame

    @property
    def error(self) -> str | None:
        return self._error

    def _run(self) -> None:
        try:
            self._render_loop()
        except Exception as error:  # surfaced in the GUI instead of dying silently
            self._error = f"Renderer stopped: {error}"
            raise

    def _render_loop(self) -> None:
        from panda3d.core import (
            GraphicsOutput,
            PerspectiveLens,
            Texture,
            loadPrcFileData,
        )

        loadPrcFileData(
            "",
            f"""
            window-type offscreen
            win-size {self._width_px} {self._height_px}
            framebuffer-multisample 1
            multisamples 4
            audio-library-name null
            sync-video false
            notify-level warning
            """,
        )
        from direct.showbase.ShowBase import ShowBase

        base = ShowBase()
        base.disableMouse()
        base.setBackgroundColor(*BACKGROUND)
        lens = PerspectiveLens()
        lens.setNearFar(1.0, 500.0)
        base.cam.node().setLens(lens)
        texture = Texture()
        base.win.addRenderTexture(texture, GraphicsOutput.RTMCopyRam)
        spinning = _build_scene(base, self._screen)

        frame_id = 0
        frame_times: deque[float] = deque(maxlen=60)
        start = time.perf_counter()
        while not self._stop.is_set():
            frame_start = time.perf_counter()
            with self._lock:
                gain = self._gain
            view = off_axis_view(self._eye_source() or DEFAULT_EYE, self._screen, gain)
            base.camera.setPos(*view.camera_position)
            base.camera.setHpr(0, 0, 0)
            lens.setFilmSize(*view.film_size)
            lens.setFilmOffset(*view.film_offset)
            lens.setFocalLength(view.focal_length)

            elapsed = frame_start - start
            for index, node in enumerate(spinning):
                node.setHpr(elapsed * (25 + 7 * index), elapsed * 15, 0)

            base.graphicsEngine.renderFrame()
            jpeg = _texture_to_jpeg(texture)
            render_ms = (time.perf_counter() - frame_start) * 1000.0

            frame_times.append(frame_start)
            fps = 0.0
            if len(frame_times) > 1:
                fps = (len(frame_times) - 1) / (frame_times[-1] - frame_times[0])
            if jpeg is not None:
                frame_id += 1
                with self._lock:
                    self._frame = RenderedFrame(jpeg, frame_id, render_ms, fps)

            remaining = self._frame_interval_s - (time.perf_counter() - frame_start)
            if remaining > 0:
                time.sleep(remaining)
        base.destroy()


def _texture_to_jpeg(texture) -> bytes | None:
    data = texture.getRamImageAs("BGR")
    if not data:
        return None
    image = np.frombuffer(bytes(data), dtype=np.uint8).reshape(
        texture.getYSize(), texture.getXSize(), 3
    )
    # Panda3D stores textures bottom row first.
    ok, encoded = cv2.imencode(".jpg", np.flipud(image), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return encoded.tobytes() if ok else None


def _build_scene(base, screen: ScreenGeometry) -> list:
    """Build a box room behind the screen, with objects inside and in front of it."""
    from panda3d.core import (
        AmbientLight,
        CardMaker,
        DirectionalLight,
        LineSegs,
        NodePath,
    )

    half_w = screen.width_mm / MM_PER_UNIT / 2.0
    half_h = screen.height_mm / MM_PER_UNIT / 2.0
    depth = ROOM_DEPTH_CM
    render = base.render

    room = render.attachNewNode("room")
    walls = CardMaker("wall")
    for name, frame, pos, hpr in (
        ("back", (-half_w, half_w, -half_h, half_h), (0, depth, 0), (0, 0, 0)),
        ("floor", (-half_w, half_w, 0, depth), (0, 0, -half_h), (0, -90, 0)),
        ("ceiling", (-half_w, half_w, -depth, 0), (0, 0, half_h), (0, 90, 0)),
        ("left", (-depth, 0, -half_h, half_h), (-half_w, 0, 0), (-90, 0, 0)),
        ("right", (0, depth, -half_h, half_h), (half_w, 0, 0), (90, 0, 0)),
    ):
        walls.setFrame(*frame)
        wall = room.attachNewNode(walls.generate())
        wall.setName(name)
        wall.setPos(*pos)
        wall.setHpr(*hpr)
        wall.setTwoSided(True)
        wall.setColor(*WALL_COLOUR)

    grid = LineSegs("grid")
    grid.setThickness(1.5)
    grid.setColor(*GRID_COLOUR)
    step = 3.0
    for y in _steps(0.0, depth, step):
        _rectangle(grid, half_w, half_h, y)
    for x in _steps(-half_w, half_w, step):
        for z in (-half_h, half_h):
            grid.moveTo(x, 0, z)
            grid.drawTo(x, depth, z)
        grid.moveTo(x, depth, -half_h)
        grid.drawTo(x, depth, half_h)
    for z in _steps(-half_h, half_h, step):
        for x in (-half_w, half_w):
            grid.moveTo(x, 0, z)
            grid.drawTo(x, depth, z)
        grid.moveTo(-half_w, depth, z)
        grid.drawTo(half_w, depth, z)
    grid_node = room.attachNewNode(grid.create())
    grid_node.setLightOff()
    # Lift the lines off the walls so they do not z-fight.
    grid_node.setDepthOffset(3)

    panda = base.loader.loadModel("models/panda")
    _fit_height(panda, 11.0)
    panda.reparentTo(render)
    panda.setPos(-half_w * 0.45, depth * 0.72, -half_h)
    panda.setH(20)

    teapot = base.loader.loadModel("models/teapot")
    _fit_height(teapot, 4.0)
    teapot.reparentTo(render)
    teapot.setPos(half_w * 0.45, depth * 0.35, -half_h)
    teapot.setColor(0.922, 0.408, 0.204, 1.0)
    teapot.setH(-30)

    spinning: list[NodePath] = []
    strings = LineSegs("strings")
    strings.setThickness(1.0)
    strings.setColor(0.765, 0.761, 0.718, 1.0)
    # Depths below zero float in front of the screen and appear to pop out of it.
    for x, y, z, size in (
        (-0.55, -6.0, 0.15, 1.6),
        (0.62, -3.0, -0.2, 1.3),
        (0.0, 8.0, 0.35, 1.8),
        (-0.2, 20.0, -0.1, 2.0),
        (0.35, 34.0, 0.3, 2.4),
    ):
        cube = base.loader.loadModel("models/misc/rgbCube")
        cube.reparentTo(render)
        cube.setScale(size)
        position = (x * half_w, y, z * half_h)
        cube.setPos(*position)
        spinning.append(cube)
        if y > 0:
            strings.moveTo(position[0], y, position[2] + size / 2)
            strings.drawTo(position[0], y, half_h)
    string_node = render.attachNewNode(strings.create())
    string_node.setLightOff()

    ambient = AmbientLight("ambient")
    ambient.setColor((0.35, 0.35, 0.35, 1))
    render.setLight(render.attachNewNode(ambient))
    sun = DirectionalLight("key")
    sun.setColor((0.85, 0.83, 0.8, 1))
    sun_path = render.attachNewNode(sun)
    sun_path.setHpr(-30, -50, 0)
    render.setLight(sun_path)
    render.setShaderAuto()
    return spinning


def _steps(start: float, stop: float, step: float) -> list[float]:
    count = math.floor((stop - start) / step + 1e-9)
    return [start + index * step for index in range(count + 1)]


def _rectangle(lines, half_w: float, half_h: float, y: float) -> None:
    lines.moveTo(-half_w, y, -half_h)
    for x, z in ((half_w, -half_h), (half_w, half_h), (-half_w, half_h), (-half_w, -half_h)):
        lines.drawTo(x, y, z)


def _fit_height(model, height: float) -> None:
    low, high = model.getTightBounds()
    model.setScale(height / (high.z - low.z))
    model.flattenLight()
    low, _ = model.getTightBounds()
    # Rest the model's base on its origin so it can stand on the floor.
    model.setZ(-low.z)
    model.flattenLight()
