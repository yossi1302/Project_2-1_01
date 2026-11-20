import os
from dataclasses import dataclass

import mediapipe as mp
import cv2
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "face_landmarker.task")
BLINK_THRESHOLD = 0.6   # score above this = eyes closed
OPEN_THRESHOLD = 0.3    # score below this = eyes open again
BLINK_HOLD_MS = 500     # eyes must stay closed this long to count

# Point in image pixel coordinates.
@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

@dataclass(frozen=True)
class EyePair:
    first: Point2D
    second: Point2D

    @property
    def midpoint(self):
        return Point2D(
            x=(self.first.x + self.second.x) / 2.0,
            y=(self.first.y + self.second.y) / 2.0,
        )

    # Distance between the eyes in pixels; shrinks as the viewer moves away.
    @property
    def separation_px(self):
        return ((self.second.x - self.first.x) ** 2 + (self.second.y - self.first.y) ** 2) ** 0.5

@dataclass(frozen=True)
class TrackingResult:
    detected: bool
    eyes: EyePair | None = None
    blink: float = 0.0

    @classmethod
    def missed(cls):
        return cls(detected=False)

# Finds the viewer's eyes in camera frames with mediapipe's face landmarker.
class Tracker:
    def __init__(self):
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=MODEL_PATH,
                delegate=mp.tasks.BaseOptions.Delegate.CPU,
            ),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    # frame is a BGR image from cv2; timestamp is in milliseconds
    # and has to increase on every call (VIDEO mode requires it).
    def find(self, frame, timestamp):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect_for_video(image, timestamp)
        if not result.face_landmarks:
            return TrackingResult.missed()

        landmarks = result.face_landmarks[0]
        height, width = frame.shape[:2]
        # Use the centre between each eye's corners, not the iris landmarks:
        # irises move when the viewer looks around the screen, which would
        # shift the estimated head position even when the head holds still.
        eyes = EyePair(
            first=_landmark_midpoint(landmarks, 33, 133, width, height),
            second=_landmark_midpoint(landmarks, 362, 263, width, height),
        )
        blink = 0.0
        if result.face_blendshapes:
            scores = {c.category_name: c.score for c in result.face_blendshapes[0]}
            blink = min(scores["eyeBlinkLeft"], scores["eyeBlinkRight"])
        return TrackingResult(detected=True, eyes=eyes, blink=blink)

    def close(self):
        self.landmarker.close()

def _landmark_midpoint(landmarks, first_index, second_index, width, height):
    first = landmarks[first_index]
    second = landmarks[second_index]
    return Point2D(
        x=(first.x + second.x) * width / 2.0,
        y=(first.y + second.y) * height / 2.0,
    )

#  deliberate blinks
class BlinkDetector:
    def __init__(self):
        self.closed_since = None
        self.fired = False

    # Returns True once per deliberate blink.
    def update(self, score, timestamp):
        if score < OPEN_THRESHOLD:
            self.closed_since = None
            self.fired = False
            return False
        if score < BLINK_THRESHOLD:
            return False
        if self.closed_since is None:
            self.closed_since = timestamp
        if not self.fired and timestamp - self.closed_since >= BLINK_HOLD_MS:
            self.fired = True
            return True
        return False