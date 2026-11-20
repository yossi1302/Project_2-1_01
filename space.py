import math

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




# One Euro filter (Casiez et al. 2012): smooths hard while the value is still
# and less while it moves fast, so tracking noise is removed without lag.
class OneEuroFilter:
    def __init__(self, *, min_cutoff, beta, d_cutoff=1.0):
        self.min_cutoff = min_cutoff  # Hz; lower = smoother when still
        self.beta = beta              # higher = less lag when moving fast
        self.d_cutoff = d_cutoff
        self.value = self.speed = self.time = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, value, time):
        if self.time is None or time <= self.time:
            self.value, self.speed, self.time = value, 0.0, time
            return value
        dt = time - self.time
        speed = (value - self.value) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self.speed = a_d * speed + (1 - a_d) * self.speed
        cutoff = self.min_cutoff + self.beta * abs(self.speed)
        a = self._alpha(cutoff, dt)
        self.value = a * value + (1 - a) * self.value
        self.time = time
        return self.value

# Smooths a stream of Eye positions; time is in seconds.
# Distance is the noisiest estimate, so it gets the strongest smoothing.
class EyeFilter:
    def __init__(self):
        self.x = OneEuroFilter(min_cutoff=1.0, beta=0.05)
        self.y = OneEuroFilter(min_cutoff=0.3, beta=0.02)
        self.z = OneEuroFilter(min_cutoff=1.0, beta=0.05)

    def __call__(self, eye, time):
        return Eye(x=self.x(eye.x, time), y=self.y(eye.y, time), z=self.z(eye.z, time))
