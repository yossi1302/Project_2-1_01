EYE_NEAR_CLIP = 15  # distance from screen of nearest possible eye position in cm

# Eye position relative to screen, in centimeters.
class Eye:
    def __init__(self, *, x, y, z):
        self.x = x
        self.y = y
        self.z = z

# Screen shape in centimeters.
class Screen:
    def __init__(self, *, width, height, cam_offset):
        self.width = width
        self.height = height
        self.cam_offset = cam_offset  # offset of camera from screen center in cm

class CameraConfig:
    def __init__(self, *, pos, film_size, film_offset, focal_length):
        self.pos = pos
        self.film_size = film_size
        self.film_offset = film_offset
        self.focal_length = focal_length

# Place the camera in panda3d space given the eye and screen
def place_camera(eye, screen):
    dist = max(eye.y, EYE_NEAR_CLIP)
    return CameraConfig(
        pos = (eye.x, -dist, eye.z),
        film_size = (screen.width, screen.height),
        film_offset = (-eye.x, -eye.z),
        focal_length = dist
    )


