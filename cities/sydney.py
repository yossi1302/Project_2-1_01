import os
import models

from panda3d.core import AmbientLight, DirectionalLight, CardMaker, TextureStage

GROUND_Z = -1.0

WATER_COLOR = (0.22, 0.38, 0.40, 1)

#def add_ocean(render):
#    return models.add_path(render, HUDSON_POINTS, HUDSON_WIDTH, WATER_COLOR, z=-0.94)

# Where the viewer stands (city x, y) and the point they face.
#SPAWN = {"position": (-22, -12), "look_at": (6, 0)}
SPAWN = {"position": (11, -14), "look_at": (-2, 8)}

def load_sydney(render, loader):
    sydney = loader.loadModel("assets/models/opera_house.glb")

    sydney.reparentTo(render)
    sydney.setScale(0.5)
    sydney.setPos(0, 10, 0)
    sydney.setHpr(70, 0, 0)

    models.place_on_ground(sydney)

    # Ambient light to make sure that cavities etc are still lit slightly
    ambientLight = AmbientLight('ambientLight')
    ambientLight.setColor((0.1, 0.1, 0.1, 1))
    ambientLightNP = render.attachNewNode(ambientLight)
    render.setLight(ambientLightNP)


    # Directional light to act as the sun
    directionalLight = DirectionalLight('directionalLight')
    directionalLight.setColor((1, 1, 0.9, 1))
    directionalLightNP = render.attachNewNode(directionalLight)
    # Facing away from the camera
    directionalLightNP.setHpr(0, -20, 0)
    render.setLight(directionalLightNP)

    # A card to act as the water
    cmaker = CardMaker("water")
    card = render.attachNewNode(cmaker.generate())
    ocean_size = 1000
    card.setScale(1000)
    card.setHpr(0, -90, 0)
    card.setPos(-ocean_size/2, -ocean_size/2, -1)
    card.setTexture(loader.loadTexture("assets/textures/ocean_seamless.jpg"))
    card.setTexScale(TextureStage.getDefault(), 5, 5)

    return sydney

    
