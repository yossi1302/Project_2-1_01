from panda3d.core import lookAt
from panda3d.core import GeomVertexFormat, GeomVertexData
from panda3d.core import Geom, GeomTriangles, GeomVertexWriter
from panda3d.core import Texture, GeomNode
from panda3d.core import PerspectiveLens
from panda3d.core import Light, Spotlight
from panda3d.core import TextNode
from panda3d.core import LVector3
from panda3d.core import RenderState, TextureAttrib
from panda3d.core import NodePath
from panda3d.core import CardMaker

import gltf
import math


def offset_polyline(points, offset):
    shifted = []
    for i, (x, y) in enumerate(points):
        before = points[max(0, i - 1)]
        after = points[min(len(points) - 1, i + 1)]
        dx, dy = after[0] - before[0], after[1] - before[1]
        length = math.hypot(dx, dy)
        if length == 0:
            raise ValueError("Cannot offset a polyline with zero-length segments.")
        shifted.append((x - dy / length * offset, y + dx / length * offset))
    return shifted

def normalized(*args):
    myVec = LVector3(*args)
    myVec.normalize()
    return myVec

def make_square(texture_path, x1, y1, z1, x2, y2, z2):
    format = GeomVertexFormat.getV3n3t2()
    vdata = GeomVertexData('square', format, Geom.UHDynamic)

    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')
    texcoord = GeomVertexWriter(vdata, 'texcoord')

    # make sure we draw the sqaure in the right plane
    if x1 != x2:
        vertex.addData3(x1, y1, z1)
        vertex.addData3(x2, y1, z1)
        vertex.addData3(x2, y2, z2)
        vertex.addData3(x1, y2, z2)

        normal.addData3(normalized(2 * x1 - 1, 2 * y1 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y1 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y2 - 1, 2 * z2 - 1))
        normal.addData3(normalized(2 * x1 - 1, 2 * y2 - 1, 2 * z2 - 1))

    else:
        vertex.addData3(x1, y1, z1)
        vertex.addData3(x2, y2, z1)
        vertex.addData3(x2, y2, z2)
        vertex.addData3(x1, y1, z2)

        normal.addData3(normalized(2 * x1 - 1, 2 * y1 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y2 - 1, 2 * z1 - 1))
        normal.addData3(normalized(2 * x2 - 1, 2 * y2 - 1, 2 * z2 - 1))
        normal.addData3(normalized(2 * x1 - 1, 2 * y1 - 1, 2 * z2 - 1))

    texcoord.addData2f(0.0, 1.0)
    texcoord.addData2f(0.0, 0.0)
    texcoord.addData2f(1.0, 0.0)
    texcoord.addData2f(1.0, 1.0)

    # Quads aren't directly supported by the Geom interface
    # you might be interested in the CardMaker class if you are
    # interested in rectangle though
    tris = GeomTriangles(Geom.UHDynamic)
    tris.addVertices(0, 1, 3)
    tris.addVertices(1, 2, 3)

    square = Geom(vdata)
    square.addPrimitive(tris)

    return square

def add_cube(render, texture_path):
    tex1 = Texture("Texture")
    tex1.setup2dTexture()
    tex1.read(texture_path)
    tex1.setMagfilter(Texture.FTNearest)
    tex1.setMinfilter(Texture.FTNearest)
    state_a = RenderState.make(TextureAttrib.make(tex1))

    # Note: it isn't particularly efficient to make every face as a separate Geom.
    # instead, it would be better to create one Geom holding all of the faces.
    square0 = make_square(texture_path, -1, -1, -1, 1, -1, 1)
    square1 = make_square(texture_path, -1, 1, -1, 1, 1, 1)
    square2 = make_square(texture_path, -1, 1, 1, 1, -1, 1)
    square3 = make_square(texture_path, -1, 1, -1, 1, -1, -1)
    square4 = make_square(texture_path, -1, -1, -1, -1, 1, 1)
    square5 = make_square(texture_path, 1, -1, -1, 1, 1, 1)
    snode = GeomNode('square')
    snode.addGeom(square0, state_a)
    snode.addGeom(square1, state_a)
    snode.addGeom(square2, state_a)
    snode.addGeom(square3, state_a)
    snode.addGeom(square4, state_a)
    snode.addGeom(square5, state_a)

    cube = render.attachNewNode(snode)
    # Static geometry for buildings: no rotation

    # OpenGl by default only draws "front faces" (polygons whose vertices are
    # specified CCW).
    cube.setTwoSided(True)
    return cube

def load_example(render):
    cube1 = add_cube(render, "./assets/example1.png")
    cube1.setPos(10, 0, 8)
    cube2 = add_cube(render, "./assets/example2.png")
    cube2.setPos(-8, 2, -2)
    cube3 = add_cube(render, "./assets/example2.png")
    cube3.setPos(11, 4, -2)
    cube3.setScale(2)

def add_ground(render):
    # Create a square ground plane using CardMaker
    cm = CardMaker("ground")
    cm.setFrame(-25, 25, -25, 25)

    ground = render.attachNewNode(cm.generate())

    # Set the ground to be horizontal
    ground.setP(-90)

    # Position the ground under the city
    ground.setPos(0, 10, -1)

    # Color the ground to a light gray
    ground.setColor(0.58, 0.62, 0.55, 1)
    ground.setLightOff()
    ground.setTwoSided(True)

    return ground

def add_model(render, file_path, position, scale=1):
    model_root = gltf.load_model(file_path)
    model = NodePath(model_root)

    model.reparentTo(render)
    model.setPos(*position)
    model.setScale(scale)
    place_on_ground(model)

    return model

def add_colored_cube(render, position, scale, color):
    cube = add_cube(render, "./assets/example1.png")

    cube.setPos(*position)
    cube.setScale(*scale)

    cube.setTextureOff(10)
    cube.setColor(*color, 10)
    cube.setLightOff(10)

    return cube


def add_roads(render, roads, road_z=-0.92, road_color=(0.28, 0.29, 0.30, 1), sidewalk_width=0.8, sidewalk_height=0.15, sidewalk_color=(0.70, 0.68, 0.62, 1)):
    for road in roads:
        points = road["points"]
        width = road["width"]
        add_path(render, points, width, road_color, z=road_z)
        for start, end in zip(points, points[1:]):
            dx, dy = end[0] - start[0], end[1] - start[1]
            length = math.hypot(dx, dy)
            if length == 0:
                continue
            nx, ny = -dy / length, dx / length
            offset = (width + sidewalk_width) / 2
            for sign in (-1, 1):
                a = (start[0] + sign * nx * offset, start[1] + sign * ny * offset)
                b = (end[0] + sign * nx * offset, end[1] + sign * ny * offset)
                add_sidewalk_segment(render, a, b, sidewalk_width, road_z, sidewalk_height, sidewalk_color)

def add_sidewalk_segment(render, start, end, width=0.8, road_z=-0.92, sidewalk_height=0.15, sidewalk_color=(0.70, 0.68, 0.62, 1)):

    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1

    length = math.sqrt(dx**2 + dy**2)

    if length == 0:
        return

    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2

    angle = math.degrees(math.atan2(dy, dx))

    sidewalk = add_colored_cube(
        render,
        position=(center_x, center_y, road_z + sidewalk_height / 2),
        scale=(length / 2, width / 2, sidewalk_height / 2),
        color=sidewalk_color
    )

    sidewalk.setH(angle)

    return sidewalk

def add_tree(render, x, y, size=1.0, ground_z=-1.0):
    trunk = (0.34, 0.27, 0.20, 1)
    leaves_dark = (0.23, 0.37, 0.25, 1)
    leaves_light = (0.31, 0.46, 0.30, 1)
    add_colored_cube(render, (x, y, ground_z + 1.0 * size), (0.14 * size, 0.14 * size, 1.0 * size), trunk)
    add_colored_cube(render, (x, y, ground_z + 2.4 * size), (0.85 * size, 0.85 * size, 0.85 * size), leaves_dark)
    add_colored_cube(render, (x, y, ground_z + 3.3 * size), (0.62 * size, 0.62 * size, 0.65 * size), leaves_light)

def add_trees(render, positions, ground_z=-1.0):
    for x, y in positions:
        add_tree(render, x, y, ground_z=ground_z)

def add_streetlamps(render, positions, ground_z=-1.0):
    for x, y in positions:
        add_streetlamp(render, x, y, ground_z=ground_z)

def add_streetlamp(render, x, y, ground_z=-1.0):

    BLACK = (0.12, 0.12, 0.13, 1)
    LIGHT = (1.0, 0.88, 0.55, 1)

    add_colored_cube(render, position=(x, y, ground_z + 0.15), scale=(0.25, 0.25, 0.15), color=BLACK)
    add_colored_cube(render, position=(x, y, ground_z + 1.5), scale=(0.08, 0.08, 1.35), color=BLACK)
    add_colored_cube(render, position=(x, y, ground_z + 2.9), scale=(0.30, 0.30, 0.08), color=BLACK)
    add_colored_cube(render, position=(x, y, ground_z + 3.25), scale=(0.22, 0.22, 0.32), color=LIGHT)
    add_colored_cube(render, position=(x, y, ground_z + 3.6), scale=(0.30, 0.30, 0.08), color=BLACK)

def add_crosswalks(render, positions, road_z=-0.92):
    for x, y, direction in positions:
        add_crosswalk(render, x, y, road_direction=direction, road_z=road_z)

def add_crosswalk(render, x, y, road_direction="horizontal", road_width=2.2, road_z=-0.92):
    STRIPE_COUNT = 5
    STRIPE_WIDTH = 0.25
    STRIPE_SPACING = 0.18

    WHITE = (0.92, 0.92, 0.86, 1)

    for i in range(STRIPE_COUNT):

        offset = (i - (STRIPE_COUNT - 1) / 2) * (STRIPE_WIDTH + STRIPE_SPACING)

        if road_direction == "horizontal":

            pos = (x + offset, y, road_z + 0.015)

            scale = (STRIPE_WIDTH / 2, road_width * 0.42, 0.01)

        else:

            pos = (x, y + offset, road_z + 0.015)

            scale = (road_width * 0.42, STRIPE_WIDTH / 2, 0.01)

        add_colored_cube(render, position=pos, scale=scale, color=WHITE)

def add_path(render, points, width, color, z=-0.95):

    if len(points) < 2:
        return None

    format = GeomVertexFormat.getV3()
    vdata = GeomVertexData("path", format, Geom.UHStatic)

    vertex = GeomVertexWriter(vdata, "vertex")

    for i, (x, y) in enumerate(points):

        if i == 0:
            dx = points[i + 1][0] - x
            dy = points[i + 1][1] - y

        elif i == len(points) - 1:
            dx = x - points[i - 1][0]
            dy = y - points[i - 1][1]

        else:
            dx = points[i + 1][0] - points[i - 1][0]
            dy = points[i + 1][1] - points[i - 1][1]

        length = math.hypot(dx, dy)

        if length == 0:
            length = 1

        nx = -dy / length
        ny = dx / length

        half_width = width / 2

        vertex.addData3(
            x + nx * half_width,
            y + ny * half_width,
            z
        )

        vertex.addData3(
            x - nx * half_width,
            y - ny * half_width,
            z
        )

    triangles = GeomTriangles(Geom.UHStatic)

    for i in range(len(points) - 1):
        a = i * 2
        b = a + 1
        c = a + 2
        d = a + 3

        triangles.addVertices(a, b, c)
        triangles.addVertices(b, d, c)

    geom = Geom(vdata)
    geom.addPrimitive(triangles)

    node = GeomNode("path")
    node.addGeom(geom)

    path = render.attachNewNode(node)

    path.setColor(*color)
    path.setTextureOff(10)
    path.setLightOff(10)
    path.setTwoSided(True)

    return path

def place_on_ground(model, ground_z=-1):
    # Get the tight bounds of the model to find its lowest point
    bounds = model.getTightBounds()

    if bounds is None:
        return

    min_point, max_point = bounds

    # Find the height of the lowest point
    bottom_z = min_point.z

    # Move the object so its base touches the ground
    model.setZ(model.getZ() + ground_z - bottom_z)

def place_on_top(model, top_z):
    bounds = model.getTightBounds()

    if bounds is None:
        return

    min_point, _ = bounds
    model.setZ(model.getZ() + top_z - min_point.z)
