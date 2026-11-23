import models

GROUND_Z = -1.0

# Where the viewer stands (city x, y) and the point they face.
# Placeholder for now: south edge, looking north across the city.
SPAWN = {"position": (0, -12), "look_at": (0, 10)}

def load_venice(render, loader):
    models.add_ground(render)
