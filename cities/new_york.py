import os
import models

GROUND_Z = -1.0
ROADS = [
    {"name": "avenue", "points": [(-8, -12), (-8, 32)], "width": 3.0},
    {"name": "street", "points": [(-22, 8), (22, 8)], "width": 3.0},
]
TREES = [(-13, -5), (-13, 15), (3, -5), (3, 15)]

def add_skyscraper(render, position, height):
    building = render.attachNewNode("Skyscraper")
    models.add_colored_cube(building, (0, 0, height / 2), (3, 3, height / 2), (0.40, 0.51, 0.61, 1))
    models.add_colored_cube(building, (0, 0, height + 0.3), (3.2, 3.2, 0.3), (0.20, 0.25, 0.30, 1))
    building.setPos(*position)
    models.place_on_ground(building)
    return building

def load_new_york(render, loader):
    models.add_ground(render)
    models.add_roads(render, ROADS)
    models.add_trees(render, TREES, GROUND_Z)
    for position, height in [((-17, 0, 0), 13), ((2, 0, 0), 18), ((12, 18, 0), 23)]:
        add_skyscraper(render, position, height)
    statue_path = "assets/models/statue_of_liberty.glb"
    if os.path.isfile(statue_path):
        statue = models.add_model(render, statue_path, (12, -10, 0), 5)
        print("Statue of Liberty loaded:", statue.getTightBounds())
    else:
        print("Statue of Liberty model not found; showing New York without it.")
