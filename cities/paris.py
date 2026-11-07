import models 
import gltf

from panda3d.core import NodePath

GROUND_Z = -1.0

BUILDINGS = [
    (-15, -9, 0), (-15, -1, 0), (-15, 7, 0), (-15, 15, 0), (-15, 23, 0),
    (-7, 28, 0), (2, 28, 0),
    (20, -17, 0), (20, -9, 0), (20, -1, 0), (20, 7, 0), (20, 15, 0), (20, 23, 0), (20, 31, 0),
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
    {"name": "shopping_road", "points": [(-25, -13), (3, -13)], "width": 2.2}
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
    (-5, 14), (-5, 17), (-5, 20), (-2, 14), (-2, 17), (-2, 20), (1, 14), (1, 17), (1, 20),
    (-21, -16), (-21, -9), (-21, -2),(-21, 5), (-21, 12), (-21, 19), (-21, 26), (-21, 33),
    (-14, 33), (-7, 33), (0, 33),
    (-5, -5), (-2, -5), (1, -5),
    (-14, 29),
]

STREETLAMPS = [
    (-21, -15),
    (-16, -15),
    (-12, -11), (-12, -5), (-12, 5), (-12, 12), (-12, 19),
    (-8, -11), (-8, -5), (-8, 5), (-8, 12), (-8, 19),
    (-4, -15), (-4, -2), (-4, 2), (-4, 22), (-4, 26), 
    (1, -15), (1, -2), (1, 2), (1, 22), (1, 26),
    (13, -12), (13, -5), (13, 5), (13, 12), (13, 19), (13, 26), (13, 33),
    (17, -12), (17, -5), (17, 5), (17, 12), (17, 19), (17, 26), (17, 33),
]

CROSSWALKS = [
    (-10, 5, "horizontal"),
    (-10, 21, "horizontal"),
    (15, 5, "horizontal"),
    (-2, -13, "vertical"),
    (-5, 0, "vertical"),
]

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

    models.place_on_ground(paris)

    models.add_ground(render)
    add_seine(render)
    add_quays(render)
    models.add_roads(render, ROADS, ROAD_Z, ROAD_COLOR, SIDEWALK_WIDTH, SIDEWALK_HEIGHT, SIDEWALK_COLOR)
    add_bridge(render)
    models.add_trees(render, TREE_POSITIONS, GROUND_Z)
    models.add_crosswalks(render, CROSSWALKS, ROAD_Z)
    models.add_streetlamps(render, STREETLAMPS, GROUND_Z)

    for position in SHOPS:
        add_shop(render, position=position)

    for position in BUILDINGS:
        add_haussmann_building(render, position=position)

    # Display the dimensions of the model
    print("Dimensions of the Eiffel Tower :", paris.getTightBounds())

    return paris

def add_seine(render):
    return models.add_path(render, SEINE_POINTS, SEINE_WIDTH, WATER_COLOR, z=-0.94)

def add_quays(render):

    distance = (SEINE_WIDTH + QUAY_WIDTH) / 2
    left = models.offset_polyline(SEINE_POINTS, distance)
    right = models.offset_polyline(SEINE_POINTS, -distance)
    models.add_path(render, left, QUAY_WIDTH, STONE_COLOR, z=-0.93)
    models.add_path(render, right, QUAY_WIDTH, STONE_COLOR, z=-0.93)


def add_haussmann_building(render, position=(0, 0, 0)):

    building = render.attachNewNode("Haussmann Building")

    # Colors for different parts of the building
    beige = (0.83, 0.79, 0.70, 1)
    grey = (0.38, 0.42, 0.45, 1)
    window_blue = (0.20, 0.28, 0.32, 1)

    # Main part of the building
    models.add_colored_cube(building, position=(0, 0, 3), scale=(3, 2, 3), color=beige)

    # Roof of the building
    models.add_colored_cube(building, position=(0, 0, 6.2), scale=(3.2, 2.2, 0.5), color=grey)

    # Windows on the building
    for floor in range(3):
        for column in range(3):
            x = -2 + column * 2
            z = 1.5 + floor * 1.8

            models.add_colored_cube(building, position=(x, -2.05, z), scale=(0.5, 0.08, 0.65), color=window_blue)

    # Add balconies on the building
    for floor in [1, 2]:
        z = 1.0 + floor * 1.8

        models.add_colored_cube(building, position=(0, -2.4, z), scale=(3.1, 0.4, 0.1), color=grey)

        # Add balcony railings
        models.add_colored_cube(building, position=(0, -2.75, z + 0.45), scale=(3.1, 0.05, 0.08), color=grey)

    building.setPos(*position)
    models.place_on_ground(building)

    return building

def add_shop(render, position=(0, 0, 0)):

    shop = render.attachNewNode("Parisian Shop")

    # Colors
    beige = (0.83, 0.79, 0.70, 1)
    grey = (0.38, 0.42, 0.45, 1)
    glass = (0.20, 0.28, 0.32, 1)
    dark = (0.16, 0.18, 0.20, 1)
    gold = (0.75, 0.58, 0.30, 1)
    awning = (0.32, 0.18, 0.22, 1)

    # Main building
    models.add_colored_cube(shop, (0, 0, 3), (5, 2, 3), beige)

    # Roof
    models.add_colored_cube(shop, (0, 0, 6.2), (5.2, 2.2, 0.5), grey)

    # Upper-floor windows
    for floor in range(2):
        for column in range(5):
            x = -4 + column * 2
            z = 3.6 + floor * 1.5

            models.add_colored_cube(shop, (x, -2.06, z), (0.55, 0.08, 0.55), glass)

    # Ground-floor shopfront
    models.add_colored_cube(shop, (0, -2.08, 1.3), (4.6, 0.12, 1.3), dark)

    # Two large display windows
    for x in [-2.8, 2.8]:
        models.add_colored_cube(shop, (x, -2.22, 1.35), (1.35, 0.06, 1.05), glass)

        # Window frame
        models.add_colored_cube(shop, (x, -2.31, 1.35), (0.05, 0.07, 1.1), gold)

    # Central entrance
    models.add_colored_cube(shop, (0, -2.25, 1.1), (0.75, 0.08, 1.1), glass)

    # Door handle
    models.add_colored_cube(shop, (0.45, -2.36, 1.1), (0.05, 0.05, 0.15), gold)

    # Shop sign above the windows
    models.add_colored_cube(shop, (0, -2.24, 2.85), (4.7, 0.16, 0.35), dark)

    # Decorative awning
    models.add_colored_cube(shop, (0, -2.65, 2.45), (4.8, 0.65, 0.12), awning)

    # Position the complete shop
    shop.setPos(*position)
    models.place_on_ground(shop)

    return shop

def add_bridge(render):
    center_x = (BRIDGE_X_MIN + BRIDGE_X_MAX) / 2
    half_length = (BRIDGE_X_MAX - BRIDGE_X_MIN) / 2
    deck_z = -0.68
    stone = (0.73, 0.70, 0.63, 1)
    parapet = (0.61, 0.59, 0.54, 1)

    models.add_colored_cube(render, (center_x, BRIDGE_Y, deck_z), (half_length, 1.45, 0.18), stone)

    for side_y in (BRIDGE_Y - 1.35, BRIDGE_Y + 1.35):
        models.add_colored_cube(render, (center_x, side_y, deck_z + 0.65), (half_length, 0.12, 0.12), parapet)
        for x in (BRIDGE_X_MIN + 0.5, center_x, BRIDGE_X_MAX - 0.5):
            models.add_colored_cube(render, (x, side_y, deck_z + 0.34), (0.13, 0.13, 0.35), parapet)
