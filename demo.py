import time

import cv2
import numpy as np

from render import Renderer

def main():
    rend = Renderer(frametime=1/60)
    rend.run()

    time.sleep(2)
    frame = rend.last_frame()

    ok, encoded = cv2.imencode(
        ".jpg", np.flipud(frame), [cv2.IMWRITE_JPEG_QUALITY, 85]
    )
    if not ok:
        print("BAD")
        return
    with open("output.jpg", "wb") as f:
        f.write(encoded.tobytes())

if __name__ == "__main__":
    main()

