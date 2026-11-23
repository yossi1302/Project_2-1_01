import models
import math
from panda3d.core import ModelNode

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
BRIDGE_Y = 11
BRIDGE_HALF_SPAN = 5     
BRIDGE_RISE = 1.5       
BRIDGE_SEGMENTS = 8
GONDOLA_SCALE = 0.6
GONDOLA_POS = (0.8, 0, -1.05)   # z: hull sits a little below the water surface 

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
        if y == BRIDGE_Y:
            continue   # leave an alley where the bridge lands
        left_color = HOUSE_COLORS[i % len(HOUSE_COLORS)]
        right_color = HOUSE_COLORS[(i + 2) % len(HOUSE_COLORS)]
        left_height = HOUSE_HEIGHTS[i % len(HOUSE_HEIGHTS)]
        right_height = HOUSE_HEIGHTS[(i + 3) % len(HOUSE_HEIGHTS)]

        add_house(render, (-5, y, 0), left_height, left_color)
        add_house(render, (5, y, 0), right_height, right_color, flip=True)

def add_bridge(render):
    bridge = render.attachNewNode("Bridge")
    stone = (0.62, 0.59, 0.54, 1)   

    # The arch .
    radius = (BRIDGE_HALF_SPAN ** 2 + BRIDGE_RISE ** 2) / (2 * BRIDGE_RISE)
    centre_z = GROUND_Z + BRIDGE_RISE - radius
    max_angle = math.asin(BRIDGE_HALF_SPAN / radius)
    step = 2 * max_angle / BRIDGE_SEGMENTS
    length = 2 * radius * math.sin(step / 2)

    for i in range(BRIDGE_SEGMENTS):
        angle = -max_angle + (i + 0.5) * step    
        x = radius * math.sin(angle)
        z = centre_z + radius * math.cos(angle)

        piece = bridge.attachNewNode("Bridge piece")
        # the deck 
        models.add_colored_cube(piece, position=(0, 0, 0), scale=(length / 2 + 0.05, 1, 0.25), color=stone)
        # low walls on both edges
        for y in (-1, 1):
            models.add_colored_cube(piece, position=(0, y, 0.45), scale=(length / 2 + 0.05, 0.08, 0.45), color=stone)

        piece.setPos(x, 0, z)
        piece.setR(math.degrees(angle))  

    bridge.setPos(0, BRIDGE_Y, 0)
    return bridge

def add_gondola(render, loader):

    holder = render.attachNewNode(ModelNode("Gondola"))
    holder.node().setPreserveTransform(ModelNode.PT_local)

    gondola = loader.loadModel("assets/models/gondola.glb")
    gondola.reparentTo(holder)

    gondola.setScale(GONDOLA_SCALE)

    #we have to copy colors from model - AI generated lines
    for part in gondola.findAllMatches("**/+GeomNode"):
        r, g, b, a = part.findAllMaterials()[0].getBaseColor()
        # glTF stores colours as linear values; ** (1 / 2.2) turns them back into screen colours
        part.setColor(r ** (1 / 2.2), g ** (1 / 2.2), b ** (1 / 2.2), 1, 1)
    gondola.setLightOff(1)
    #end of AI code

    holder.setPos(*GONDOLA_POS)
    holder.setH(4)   # turned a little
    return holder

# Called every frame 
def animate(scene, t):
    gondola = scene.find("**/Gondola")
    if gondola.isEmpty():
        return
    gondola.setR(2 * math.sin(t * 1.3))                          # rocks side to side
    gondola.setP(0.8 * math.sin(t * 0.9))                        # bow up and down a little
    gondola.setZ(GONDOLA_POS[2] + 0.04 * math.sin(t * 1.7))      # bobs on the water







def load_venice(render, loader):
    models.add_ground(render)
    add_canal(render)
    add_houses_group(render)
    add_bridge(render)
    add_gondola(render, loader)
