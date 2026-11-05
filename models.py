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

import render

GROUND_Z = -1.0

BUILDINGS = [
    (-15, 7, 0), (-15, 15, 0), (-15, 23, 0),
    (-7, 28, 0), (2, 28, 0),
    (20, -1, 0), (20, 7, 0), (20, 15, 0), (20, 23, 0), (20, 31, 0),
]

SHOPS = [(-3, -9, 0)]

SEINE_POINTS = [
    (7.5, -15), (8.5, -5), (8.0, 0),
    (9.0, 5), (8.5, 10), (7.5, 15),
    (8.0, 20), (9.0, 25), (10.0, 35),
]

SEINE_WIDTH = 5.5
QUAY_WIDTH = 1.0

ROADS = [
    {"name": "west_road", "points": [(-10, -11), (-10, 22)], "width": 2.2},
    {"name": "north_road", "points": [(-12, 24), (5, 24)], "width": 2.2},
    {"name": "south_road", "points": [(-8, 0), (3, 0)], "width": 2.2},
    {"name": "east_road", "points": [(15, -15), (15, 35)], "width": 2.2},
    {"name": "shopping_road", "points": [(-20, -13), (3, -13)], "width": 2.2}
]

SIDEWALK_WIDTH = 0.8
SIDEWALK_HEIGHT = 0.15
SIDEWALK_COLOR = (0.70, 0.68, 0.62, 1)

ROAD_Z = -0.92
ROAD_COLOR = (0.28, 0.29, 0.30, 1)
WATER_COLOR = (0.22, 0.38, 0.40, 1)
STONE_COLOR = (0.67, 0.65, 0.59, 1)

BRIDGE_Y = 0.0
BRIDGE_X_MIN = 3.0
BRIDGE_X_MAX = 13.5

TREE_POSITIONS = [
    (-5, 17), (-5, 20), (-2, 17), (-2, 20), (1, 17), (1, 20),
    (-21, 5), (-21, 12), (-21, 19), (-21, 26), (-21, 33),
]

STREETLAMPS = [
    (-12, 5),
    (-12, 12),
    (-12, 19),

    (-8, 5),
    (-8, 12),
    (-8, 19),

    (13, 5),
    (13, 12),
    (13, 19),

    (17, 5),
    (17, 12),
    (17, 19),

    (-5, -2),
    (-5, 2),
    (0, -2),
    (0, 2),
]

CROSSWALKS = [
    (-10, 5, "horizontal"),
    (-10, 21, "horizontal"),
    (15, 5, "horizontal"),
    (-2, -13, "vertical"),
    (-5, 0, "vertical"),
]

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

def load_paris(render, loader):
    # Charge GLTF file
    model_root = gltf.load_model("assets/models/tour_eiffel.glb")

    # Convert the model to a Panda3D NodePath
    paris = NodePath(model_root)

    paris.reparentTo(render)
    paris.setPos(-2, 8, 0)
    paris.setScale(8)

    paris.setTextureOff(1)
    paris.setColorOff(1)
    paris.setColor(0.42, 0.42, 0.42, 1)
    paris.setLightOff(1)

    place_on_ground(paris)

    add_ground(render)
    add_seine(render)
    add_quays(render)
    add_roads(render)
    add_bridge(render)
    add_trees(render)
    add_crosswalks(render)
    add_streetlamps(render)

    for position in SHOPS:
        add_shop(render, position=position)

    for position in BUILDINGS:
        add_haussmann_building(render, position=position)

    # Display the dimensions of the model
    print("Dimensions of the Eiffel Tower :", paris.getTightBounds())

    return paris

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

def add_seine(render):
    return add_path(render, SEINE_POINTS, SEINE_WIDTH, WATER_COLOR, z=-0.94)

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

def add_haussmann_building(render, position=(0, 0, 0)):

    building = render.attachNewNode("Haussmann Building")

    # Colors for different parts of the building
    beige = (0.83, 0.79, 0.70, 1)
    grey = (0.38, 0.42, 0.45, 1)
    window_blue = (0.20, 0.28, 0.32, 1)

    # Main part of the building
    add_colored_cube(building, position=(0, 0, 3), scale=(3, 2, 3), color=beige)

    # Roof of the building
    add_colored_cube(building, position=(0, 0, 6.2), scale=(3.2, 2.2, 0.5), color=grey)

    # Windows on the building
    for floor in range(3):
        for column in range(3):
            x = -2 + column * 2
            z = 1.5 + floor * 1.8

            add_colored_cube(building, position=(x, -2.05, z), scale=(0.5, 0.08, 0.65), color=window_blue)

    # Add balconies on the building
    for floor in [1, 2]:
        z = 1.0 + floor * 1.8

        add_colored_cube(building, position=(0, -2.4, z), scale=(3.1, 0.4, 0.1), color=grey)

        # Add balcony railings
        add_colored_cube(building, position=(0, -2.75, z + 0.45), scale=(3.1, 0.05, 0.08), color=grey)

    building.setPos(*position)
    place_on_ground(building)

    return building

def add_shop(render, position=(0, 0, 0)):
        
    for shops in SHOPS:

        shops = render.attachNewNode("Shop")

        beige = (0.83, 0.79, 0.70, 1)
        grey = (0.38, 0.42, 0.45, 1)
        window_blue = (0.20, 0.28, 0.32, 1)
        blue = (0.10, 0.25, 0.32, 1)
        white = (0.92, 0.92, 0.86, 1)
        red = (0.80, 0.20, 0.20, 1)

        # Main part of the building
        add_colored_cube(shops, position=(0, 0, 3), scale=(5, 2, 3), color=beige)

        # Roof of the building
        add_colored_cube(shops, position=(0, 0, 6.2), scale=(5.2, 2.2, 0.5), color=grey)

        # Windows on the building
        for column in range(5):
            x = -2.1 + column * 2

            add_colored_cube(shops, position=(x, -3.5, 6.4), scale=(0.5, 0.08, 0.65), color=window_blue)

        # Small flags on the building
        for column in range(6):
            x = -2.3 + column * 1.5

            add_colored_cube(shops, position=(x, -3.5, 5.2), scale=(0.2, 0.08, 0.2), color=blue)
            add_colored_cube(shops, position=(x + 0.5, -3.5, 5.2), scale=(0.2, 0.08, 0.2), color=white)
            add_colored_cube(shops, position=(x + 1, -3.5, 5.2), scale=(0.2, 0.08, 0.2), color=red)

        shops.setPos(*position)
        place_on_ground(shops)

        return shops

def add_quays(render):

    distance = (SEINE_WIDTH + QUAY_WIDTH) / 2
    left = offset_polyline(SEINE_POINTS, distance)
    right = offset_polyline(SEINE_POINTS, -distance)
    add_path(render, left, QUAY_WIDTH, STONE_COLOR, z=-0.93)
    add_path(render, right, QUAY_WIDTH, STONE_COLOR, z=-0.93)

def add_roads(render):

    for road in ROADS:

        points = road["points"]
        road_width = road["width"]

        add_path(render, points=points, width=road_width, color=ROAD_COLOR, z=ROAD_Z)

        # Add sidewalks on both sides of the road
        for i in range(len(points) - 1):

            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            dx = x2 - x1
            dy = y2 - y1

            length = math.sqrt(dx**2 + dy**2)

            if length == 0:
                continue

            nx = -dy / length
            ny = dx / length

            offset = (road_width + SIDEWALK_WIDTH) / 2

            left_start = (x1 + nx * offset, y1 + ny * offset)
            left_end = (x2 + nx * offset, y2 + ny * offset)
            right_start = (x1 - nx * offset, y1 - ny * offset)
            right_end = (x2 - nx * offset, y2 - ny * offset)

            add_sidewalk_segment(render, left_start, left_end, SIDEWALK_WIDTH)
            add_sidewalk_segment(render, right_start, right_end, SIDEWALK_WIDTH)

def add_sidewalk_segment(render, start, end, width=0.8):

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
        position=(center_x, center_y, ROAD_Z + SIDEWALK_HEIGHT / 2),
        scale=(length / 2, width / 2, SIDEWALK_HEIGHT / 2),
        color=SIDEWALK_COLOR
    )

    sidewalk.setH(angle)

    return sidewalk

def add_bridge(render):
    center_x = (BRIDGE_X_MIN + BRIDGE_X_MAX) / 2
    half_length = (BRIDGE_X_MAX - BRIDGE_X_MIN) / 2
    deck_z = -0.68
    stone = (0.73, 0.70, 0.63, 1)
    parapet = (0.61, 0.59, 0.54, 1)

    add_colored_cube(render, (center_x, BRIDGE_Y, deck_z), (half_length, 1.45, 0.18), stone)

    for side_y in (BRIDGE_Y - 1.35, BRIDGE_Y + 1.35):
        add_colored_cube(render, (center_x, side_y, deck_z + 0.65), (half_length, 0.12, 0.12), parapet)
        for x in (BRIDGE_X_MIN + 0.5, center_x, BRIDGE_X_MAX - 0.5):
            add_colored_cube(render, (x, side_y, deck_z + 0.34), (0.13, 0.13, 0.35), parapet)

def add_tree(render, x, y, size=1.0):
    trunk = (0.34, 0.27, 0.20, 1)
    leaves_dark = (0.23, 0.37, 0.25, 1)
    leaves_light = (0.31, 0.46, 0.30, 1)
    add_colored_cube(render, (x, y, GROUND_Z + 1.0 * size), (0.14 * size, 0.14 * size, 1.0 * size), trunk)
    add_colored_cube(render, (x, y, GROUND_Z + 2.4 * size), (0.85 * size, 0.85 * size, 0.85 * size), leaves_dark)
    add_colored_cube(render, (x, y, GROUND_Z + 3.3 * size), (0.62 * size, 0.62 * size, 0.65 * size), leaves_light)

def add_trees(render):
    for x, y in TREE_POSITIONS:
        add_tree(render, x, y)

def add_streetlamps(render):

    for x, y in STREETLAMPS:
        add_streetlamp(render, x, y)

def add_streetlamp(render, x, y):

    BLACK = (0.12, 0.12, 0.13, 1)
    LIGHT = (1.0, 0.88, 0.55, 1)

    add_colored_cube(render, position=(x, y, GROUND_Z + 0.15), scale=(0.25, 0.25, 0.15), color=BLACK)
    add_colored_cube(render, position=(x, y, GROUND_Z + 1.5), scale=(0.08, 0.08, 1.35), color=BLACK)
    add_colored_cube(render, position=(x, y, GROUND_Z + 2.9), scale=(0.30, 0.30, 0.08), color=BLACK)
    add_colored_cube(render, position=(x, y, GROUND_Z + 3.25), scale=(0.22, 0.22, 0.32), color=LIGHT)
    add_colored_cube(render, position=(x, y, GROUND_Z + 3.6), scale=(0.30, 0.30, 0.08), color=BLACK)
    
def add_crosswalks(render):

    for x, y, direction in CROSSWALKS:

        add_crosswalk(render, x, y, road_direction=direction)

def add_crosswalk(render, x, y, road_direction="horizontal", road_width=2.2):
    STRIPE_COUNT = 5
    STRIPE_WIDTH = 0.25
    STRIPE_SPACING = 0.18

    WHITE = (0.92, 0.92, 0.86, 1)

    for i in range(STRIPE_COUNT):

        offset = (i - (STRIPE_COUNT - 1) / 2) * (STRIPE_WIDTH + STRIPE_SPACING)

        if road_direction == "horizontal":

            pos = (x + offset, y, ROAD_Z + 0.015)

            scale = (STRIPE_WIDTH / 2, road_width * 0.42, 0.01)

        else:

            pos = (x, y + offset, ROAD_Z + 0.015)

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
