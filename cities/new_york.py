import os
import models

GROUND_Z = -1.0

BUILDINGS = [
    [(-17, 0, 0), 9],
    [(2, 0, 0), 9],
    [(12, 18, 0), 12]
]

HUDSON_POINTS = [
    (-11, -3), (-10, 0), (-8, 3), (-6, 4), (-3, 5), (0, 4), (1, 2), (4, -1), 
    (4, -3), (4, -5), (3, -7), (0, -10), (-3, -11), (-6, -10), (-9, -8), (-10, -6),
    (-11, -3), (-16, -4), (-22, -6),
    (-11, -3), (-10, -6), (-9, -8), (-6, -10), (-3, -11), (0, -10), (3, -7), (4, -5), (4, -3),
    (6, -3), (9, -4), (16, -3), (22, 0),
]

HUDSON_WIDTH = 5.0

ROADS = [
    {"name": "avenue", "points": [(-18, -12), (-18, 32)], "width": 3.0},
    {"name": "street", "points": [(-22, 12), (22, 12)], "width": 3.0},
]

WATER_COLOR = (0.22, 0.38, 0.40, 1)

TREES = [(-13, -5), (-13, -10), (4, -8), (3, 15)]

def add_hudson(render):
    return models.add_path(render, HUDSON_POINTS, HUDSON_WIDTH, WATER_COLOR, z=-0.94)

# Where the viewer stands (city x, y) and the point they face.
# South-west corner, looking east across the avenue: skyline ahead,
# Statue of Liberty on the right.
SPAWN = {"position": (-22, -12), "look_at": (6, 0)}

def add_skyscraper(render, position, height):
    building = render.attachNewNode("Skyscraper")

    models.add_colored_cube(building, (0, 0, height / 2), (3, 3, height / 2), (0.40, 0.51, 0.61, 1))
    models.add_colored_cube(building, (0, 0, height + 0.3), (3.2, 3.2, 0.3), (0.20, 0.25, 0.30, 1))

    building.setPos(*position)
    models.place_on_ground(building)

    return building

def load_new_york(render, loader):
    new_york = loader.loadModel("assets/models/statue_of_liberty.glb")

    new_york.reparentTo(render)
    new_york.setScale(0.1)
    new_york.setPos(-3, -3, 0)

    models.place_on_ground(new_york)

    models.add_ground(render)
    models.add_roads(render, ROADS)
    add_hudson(render)
    models.add_trees(render, TREES, GROUND_Z)

    for position, height in BUILDINGS:
        add_skyscraper(render, position, height)

    return new_york

    
