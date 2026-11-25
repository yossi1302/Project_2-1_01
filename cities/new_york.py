import os
import models

GROUND_Z = -1.0

BUILDINGS = [
    [(7, 6.5, 0), 7], [(14, 6.5, 0), 9], [(21, 6.5, 0), 11],
    [(7, 17.5, 0), 9], [(14, 17.5, 0), 15], [(21, 17.5, 0), 12],
    [(7, 28.5, 0), 11], [(14, 28.5, 0), 17], [(21, 28.5, 0), 15],
    [(-14, 6.5, 0), 7], [(-21, 6.5, 0), 9],
    [(-14, 17.5, 0), 9], [(-21, 17.5, 0), 15],
    [(-14, 28.5, 0), 11], [(-21, 28.5, 0), 17],

]

HUDSON_POINTS = [
    (-11, -3), (-10, 0), (-8, 3), (-6, 4), (-3, 5), (0, 4), (2, 2), (4, -1), 
    (4, -3), (4, -5), (3, -7), (0, -10), (-3, -11), (-6, -10), (-9, -8), (-10, -6),
    (-11, -3), (-16, -4), (-22, -6),
    (-11, -3), (-10, -6), (-9, -8), (-6, -10), (-3, -11), (0, -10), (3, -7), (4, -5), (4, -3),
    (6, -3), (9, -4), (16, -3), (20, 0), (24.5, -1)
]

HUDSON_WIDTH = 5.0

ROADS = [
    {"name": "main_street", "points": [(-3, 14), (-3, 33)], "width": 3.0},
    {"name": "street1", "points": [(-25, 12), (25, 12)], "width": 3.0},
    {"name": "street2", "points": [(-25, 23), (-5, 23)], "width": 3.0},
    {"name": "street3", "points": [(-1, 23), (25, 23)], "width": 3.0},
]

SIDEWALK_WIDTH = 0.8
SIDEWALK_HEIGHT = 0.15
SIDEWALK_COLOR = (0.60, 0.58, 0.62, 1)

ROAD_Z = -0.92
ROAD_COLOR = (0.28, 0.29, 0.30, 1)
WATER_COLOR = (0.22, 0.38, 0.40, 1)

TREES = [
    (-13, -5), (-13, -10), 
    (4, -13), (7, -13), (10, -13), (13, -13), (16, -13), (19, -13), (22, -13),
    (6, -10), (9, -10), (12, -10), (15, -10), (18, -10), (21, -10),
    (7, 1), (10, 1), (13, 1), (16, 1), 
    (7.5, -7), (10.5, -7), (13.5, -7), (16.5, -7), (19.5, -7), (22.5, -7)
]

STREETLAMPS = [
    (-3, -8), (0, -6), (0, 0), (1, -3),
    (-3, 2), (-7, -6), (-7, 1), (-8, -3)
]

TRAFFIC_LIGHTS = [
    (-6, 15), (0, 9), (0, 26),
    (-6, 20),
    (1, 22), (1, 11)
]

TAXIS = [
    (9, 11.25, 0),
    (-10, 12.75, 180),
    (-3.75, 29, 90)
]

CROSSWALKS = [
    (-3, 18, "horizontal"),
    (5, 12, "vertical"),
    (-18, 12, "vertical"),
    (-9, 23, "vertical"),
    (6, 23, "vertical"),
]

# Where the viewer stands (city x, y) and the point they face.
# South-west corner, looking east across the avenue: skyline ahead,
# Statue of Liberty on the right.
SPAWN = {"position": (-22, -12), "look_at": (6, 0)}

def add_hudson(render):
    return models.add_path(render, HUDSON_POINTS, HUDSON_WIDTH, WATER_COLOR, z=-0.94)

def add_traffic_light(render, x, y, ground_z=-1.0):

    BLACK = (0.12, 0.12, 0.13, 1)
    RED = (0.95, 0.10, 0.10, 1)
    YELLOW = (1.0, 0.80, 0.05, 1)
    GREEN = (0.10, 0.85, 0.25, 1)

    models.add_colored_cube(render, (x, y, ground_z + 0.15), (0.25, 0.25, 0.15), BLACK)
    models.add_colored_cube(render, (x, y, ground_z + 1.5), (0.08, 0.08, 1.35), BLACK)
    models.add_colored_cube(render, (x, y, ground_z + 3.25), (0.32, 0.32, 0.50), BLACK)

    lights = [
        (3.55, RED), (3.25, YELLOW), (2.95, GREEN)
    ]

    for height, color in lights:
        z = ground_z + height

        for side in (-1, 1):

            # Left and right faces
            models.add_colored_cube(render, (x + side * 0.33, y, z), (0.02, 0.12, 0.12), color)

            # Front and back faces
            models.add_colored_cube(render, (x, y + side * 0.33, z), (0.12, 0.02, 0.12), color)

def add_traffic_lights(render, positions, ground_z=-1.0):
    for x, y in positions:
        add_traffic_light(render, x, y, ground_z=ground_z)

def add_taxi(render, x, y, heading=0, road_z=-0.92):

    YELLOW = (1.0, 0.76, 0.05, 1)
    BLACK = (0.10, 0.10, 0.12, 1)
    GLASS = (0.20, 0.32, 0.40, 1)
    WHITE = (1.0, 0.95, 0.80, 1)
    RED = (0.90, 0.10, 0.10, 1)
    GREY = (0.45, 0.45, 0.48, 1)

    taxi = render.attachNewNode("Taxi")

    models.add_colored_cube(taxi, (0, 0, 0.30), (0.90, 0.43, 0.18), YELLOW)
    models.add_colored_cube(taxi, (-0.10, 0, 0.59), (0.48, 0.35, 0.15), GLASS)
    models.add_colored_cube(taxi, (-0.10, 0, 0.76), (0.50, 0.37, 0.04), YELLOW)
    models.add_colored_cube(taxi, (-0.10, 0, 0.85), (0.16, 0.12, 0.05), WHITE)

    # Wheels
    for wheel_x in (-0.55, 0.55):
        for side in (-1, 1):

            models.add_colored_cube(taxi, (wheel_x, side * 0.43, 0.16), (0.18, 0.09, 0.16), BLACK)
            models.add_colored_cube(taxi, (wheel_x, side * 0.53, 0.16), (0.08, 0.02, 0.08), GREY)

    # Headlights and rear lights
    for side in (-1, 1):

        models.add_colored_cube(taxi, (0.91, side * 0.28, 0.33), (0.02, 0.10, 0.07), WHITE)
        models.add_colored_cube(taxi, (-0.91, side * 0.28, 0.33), (0.02, 0.10, 0.07), RED)

    taxi.flattenStrong()

    taxi.setPos(x, y, road_z)
    taxi.setH(heading)

    return taxi

def add_taxis(render, positions, road_z=-0.92):
    for x, y, heading in positions:
        add_taxi(render, x, y, heading, road_z)

def add_windows(building, width, depth, height):
    WINDOW_COLOR = (0.16, 0.23, 0.30, 1)

    WINDOW_WIDTH = 0.8
    WINDOW_HEIGHT = 1.0
    WINDOW_THICKNESS = 0.02

    COLUMN_SPACING = 1.3
    FLOOR_SPACING = 1.6

    floors = int(height / FLOOR_SPACING)

    columns_x = int(width / COLUMN_SPACING)
    columns_y = int(depth / COLUMN_SPACING)

    windows = building.attachNewNode("Windows")

    for floor in range(floors):
        z = (floor + 0.5) * FLOOR_SPACING

        # Front and back facades
        for column in range(columns_x):
            x = (column - (columns_x - 1) / 2) * COLUMN_SPACING

            for side in (-1, 1):
                y = side * (depth / 2 + 0.01)

                models.add_colored_cube(windows, (x, y, z), (WINDOW_WIDTH / 2, WINDOW_THICKNESS, WINDOW_HEIGHT / 2), WINDOW_COLOR)

        # Left and right facades
        for column in range(columns_y):
            y = (column - (columns_y - 1) / 2) * COLUMN_SPACING

            for side in (-1, 1):
                x = side * (width / 2 + 0.01)

                models.add_colored_cube(windows, (x, y, z), (WINDOW_THICKNESS, WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2), WINDOW_COLOR)

    windows.flattenStrong()

    return windows

def add_skyscraper(render, position, height):
    building = render.attachNewNode("Skyscraper")

    # Main building
    models.add_colored_cube(building, (0, 0, height / 2), (3, 3, height / 2), (0.40, 0.51, 0.61, 1))

    # Roof
    models.add_colored_cube(building, (0, 0, height + 0.3), (3.2, 3.2, 0.3), (0.20, 0.25, 0.30, 1))

    # Windows
    add_windows(building, 6, 6, height)

    building.setPos(*position)
    models.place_on_ground(building)

    return building

def load_new_york(render, loader):
    new_york = loader.loadModel("assets/models/statue_of_liberty.glb")

    new_york.reparentTo(render)
    new_york.setScale(0.15)
    new_york.setPos(-3, -3, 0)

    models.place_on_ground(new_york)

    models.add_ground(render)
    models.add_roads(render, ROADS)
    add_hudson(render)
    models.add_trees(render, TREES, GROUND_Z)
    models.add_crosswalks(render, CROSSWALKS, ROAD_Z)
    models.add_streetlamps(render, STREETLAMPS, GROUND_Z)
    add_traffic_lights(render, TRAFFIC_LIGHTS, GROUND_Z)
    add_taxis(render, TAXIS, ROAD_Z)

    for position, height in BUILDINGS:
        add_skyscraper(render, position, height)

    return new_york

    
