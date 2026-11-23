import models

GROUND_Z = -1.0
CANAL_POINTS = [(0, -15), (0, 35)]
CANAL_WIDTH = 6.0
WATER_COLOR = (0.18, 0.42, 0.42, 1)
HOUSE_COLORS = [
    (0.86, 0.62, 0.36, 1),  # ochre
    (0.78, 0.40, 0.30, 1),  # terracotta
    (0.90, 0.68, 0.66, 1),  # pink
    (0.93, 0.85, 0.70, 1),  # cream
    (0.72, 0.30, 0.28, 1),  # venetian red
]
HOUSE_HEIGHTS = [7, 9, 8, 10, 7.5]

SPAWN = {"position": (0, -12), "look_at": (0, 10)}

def add_canal(render):
    return models.add_path(render, CANAL_POINTS, CANAL_WIDTH, WATER_COLOR, z=-0.94)

def add_house(render, position, height, color, flip=False):
    house = render.attachNewNode("Canal House")

    window = (0.20, 0.22, 0.25, 1)
    roof = (0.55, 0.25, 0.18, 1)

    # block
    models.add_colored_cube(house, position=(0, 0, height / 2), scale=(2, 2, height / 2), color=color)

    # Flat roof
    models.add_colored_cube(house, position=(0, 0, height + 0.15), scale=(2.1, 2.1, 0.15), color=roof)

    # windows
    floors = int((height - 1) // 2.5)
    for floor in range(floors):
        z = 1.5 + floor * 2.5
        for y in (-1, 1):
            models.add_colored_cube(house, position=(2.05, y, z), scale=(0.08, 0.4, 0.6), color=window)

    house.setPos(*position)
    if flip:
        house.setH(180)   
    models.place_on_ground(house)

    return house

def add_houses_group(render):
    for i, y in enumerate(range(-13, 35, 4)):
        left_color = HOUSE_COLORS[i % len(HOUSE_COLORS)]
        right_color = HOUSE_COLORS[(i + 2) % len(HOUSE_COLORS)]
        left_height = HOUSE_HEIGHTS[i % len(HOUSE_HEIGHTS)]
        right_height = HOUSE_HEIGHTS[(i + 3) % len(HOUSE_HEIGHTS)]

        add_house(render, (-5, y, 0), left_height, left_color)
        add_house(render, (5, y, 0), right_height, right_color, flip=True)

def load_venice(render, loader):
    models.add_ground(render)
    add_canal(render)
    add_houses_group(render)
