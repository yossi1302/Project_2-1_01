import os
import models

GROUND_Z = -1.0

MEUSE_POINTS = [
    (0, -15), (0, 35)
]

RAILWAYS = [
    (23.5, 12.5, 45, 0)
]

ROADS = [
    {"name": "Paul-Henri Spaaklaan", "points": [(4, 15.2), (22, 15.2)], "width": 3.0},
    {"name": "Center", "points": [(-25, 15.2), (-4, 15.2)], "width": 3.0},
    {"name": "Town", "points": [(14, -15), (14, 13)], "width": 2.0},
]

MEUSE_WIDTH = 5.0
QUAY_WIDTH = 1.0

WATER_COLOR = (0.22, 0.38, 0.40, 1)
STONE_COLOR = (0.67, 0.65, 0.59, 1)

UNIVERSITY_POSITION = (14, 23, 0)

UNIVERSITY_BEIGE = (0.82, 0.79, 0.68, 1)
UNIVERSITY_BLACK = (0.15, 0.15, 0.16, 1)
UNIVERSITY_GLASS = (0.21, 0.31, 0.38, 1)
UNIVERSITY_FRAME = (0.65, 0.67, 0.68, 1)

WING_WIDTH = 4.5
WING_DEPTH = 10.0
WING_HEIGHT = 7.0

CENTRAL_SIZE = 5.0
CENTRAL_HEIGHT = 2.5

SPAWN = {"position": (-22, -12), "look_at": (6, 0)}

def add_meuse(render):
    return models.add_path(render, MEUSE_POINTS, MEUSE_WIDTH, WATER_COLOR, z=-0.94)

def add_quays(render):

    distance = (MEUSE_WIDTH + QUAY_WIDTH) / 2
    left = models.offset_polyline(MEUSE_POINTS, distance)
    right = models.offset_polyline(MEUSE_POINTS, -distance)
    models.add_path(render, left, QUAY_WIDTH, STONE_COLOR, z=-0.93)
    models.add_path(render, right, QUAY_WIDTH, STONE_COLOR, z=-0.93)

def add_railway(render, x, y, length, heading=0, ground_z=-1.0):

    BALLAST = (0.45, 0.43, 0.40, 1)
    WOOD = (0.30, 0.22, 0.16, 1)
    STEEL = (0.55, 0.57, 0.60, 1)

    railway = render.attachNewNode("Railway")

    models.add_colored_cube(railway, (0, 0, 0.05), (1.0, length / 2, 0.05), BALLAST)

    spacing = 0.45
    sleeper_count = int(length / spacing)

    for i in range(sleeper_count):

        offset = (i - (sleeper_count - 1) / 2) * spacing

        models.add_colored_cube(railway, (0, offset, 0.15), (0.85, 0.12, 0.05), WOOD)

    for side in (-1, 1):

        models.add_colored_cube(railway, (side * 0.60, 0, 0.27), (0.05, length / 2, 0.07), STEEL)

    railway.flattenStrong()

    railway.setPos(x, y, ground_z)
    railway.setH(heading)

    return railway

def add_university_windows(building, width, depth, height, floors):

    windows = building.attachNewNode("Windows")

    floor_spacing = height / floors
    window_height = 0.55
    window_thickness = 0.025
    frame_spacing = 0.65
    margin = 0.25

    for floor in range(floors):

        z = (floor + 0.5) * floor_spacing

        # Front and rear facades
        band_width = width - 2 * margin
        columns = max(1, int(band_width / frame_spacing))

        for side in (-1, 1):

            y = side * (depth / 2 + window_thickness)

            models.add_colored_cube(windows, (0, y, z), (band_width / 2, window_thickness, window_height / 2), UNIVERSITY_GLASS)

            # Vertical window frames
            for column in range(1, columns):

                x = -band_width / 2 + (column * band_width / columns)

                models.add_colored_cube(windows, (x, y + side * 0.03, z), (0.025, 0.015, window_height / 2), UNIVERSITY_FRAME)

        # Left and right facades
        band_depth = depth - 2 * margin
        columns = max(1, int(band_depth / frame_spacing))

        for side in (-1, 1):

            x = side * (width / 2 + window_thickness)

            models.add_colored_cube(windows, (x, 0, z), (window_thickness, band_depth / 2, window_height / 2), UNIVERSITY_GLASS)

            # Vertical window frames
            for column in range(1, columns):

                y = -band_depth / 2 + (column * band_depth / columns)

                models.add_colored_cube(windows, (x + side * 0.03, y, z), (0.015, 0.025, window_height / 2), UNIVERSITY_FRAME)

    windows.flattenStrong()

    return windows

def add_university_wing(render, position):

    wing = render.attachNewNode("UniversityWing")

    models.add_colored_cube(wing, (0, 0, WING_HEIGHT / 2), (WING_WIDTH / 2, WING_DEPTH / 2, WING_HEIGHT / 2), UNIVERSITY_BEIGE)
    models.add_colored_cube(wing, (0, 0, WING_HEIGHT + 0.05), (WING_WIDTH / 2, WING_DEPTH / 2, 0.05), UNIVERSITY_BEIGE)

    add_university_windows(wing, WING_WIDTH, WING_DEPTH, WING_HEIGHT, floors=5)

    wing.setPos(*position)

    return wing

def add_university_door(building, width, depth):

    door = building.attachNewNode("Entrance")

    DOOR_WIDTH = 1.6
    DOOR_HEIGHT = 1.8
    FRAME_WIDTH = 0.05

    y = -depth / 2 - 0.08

    models.add_colored_cube(door, (0, y, DOOR_HEIGHT / 2), (DOOR_WIDTH / 2 + FRAME_WIDTH, 0.06, DOOR_HEIGHT / 2), UNIVERSITY_FRAME)

    for side in (-1, 1):

        models.add_colored_cube(door, 
                                (side * DOOR_WIDTH / 4, y - 0.06, DOOR_HEIGHT / 2), 
                                (DOOR_WIDTH / 4 - FRAME_WIDTH, 0.025, DOOR_HEIGHT / 2 - FRAME_WIDTH), 
                                UNIVERSITY_GLASS)

        models.add_colored_cube(door, (side * 0.12, y - 0.10, 0.95), (0.025, 0.035, 0.15), UNIVERSITY_FRAME)

    return door

def add_university_center(render, position):

    center = render.attachNewNode("UniversityCenter")

    models.add_colored_cube(center, (0, 0, CENTRAL_HEIGHT / 2), (CENTRAL_SIZE / 2, CENTRAL_SIZE / 2, CENTRAL_HEIGHT / 2), UNIVERSITY_BLACK)
    models.add_colored_cube(center, (0, 0, CENTRAL_HEIGHT + 0.05), (CENTRAL_SIZE / 2, CENTRAL_SIZE / 2, 0.05), UNIVERSITY_BLACK)

    add_university_windows(center, CENTRAL_SIZE, CENTRAL_SIZE, CENTRAL_HEIGHT, floors=1)

    add_university_door(center, CENTRAL_SIZE, CENTRAL_SIZE)

    center.setPos(*position)

    return center

def add_university(render, position):

    university = render.attachNewNode("University")

    wing_offset = (WING_WIDTH + CENTRAL_SIZE) / 2
    center_offset = 0

    # Left wing
    add_university_wing(university, (-wing_offset, 0, 0))
    # Right wing
    add_university_wing(university, (wing_offset, 0, 0))
    # Central black building
    add_university_center(university, (0, center_offset, 0))

    university.flattenStrong()
    university.setPos(*position)

    models.place_on_ground(university)

    return university

def load_maastricht(render, loader):

    models.add_ground(render)
    models.add_roads(render, ROADS)
    add_meuse(render)
    add_quays(render)

    for x, y, length, heading in RAILWAYS:
        add_railway(render, x, y, length, heading, GROUND_Z)

    add_university(render, UNIVERSITY_POSITION)

    return
