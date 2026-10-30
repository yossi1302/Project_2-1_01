import os
from dataclasses import dataclass

import mediapipe as mp
import cv2
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "face_landmarker.task")

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
        if len(landmarks) >= 478:
            # Models with iris landmarks: use the iris centres directly.
            first = landmarks[468]
            second = landmarks[473]
            eyes = EyePair(
                first=Point2D(first.x * width, first.y * height),
                second=Point2D(second.x * width, second.y * height),
            )
        else:
            # Otherwise use the midpoint between each eye's corners.
            eyes = EyePair(
                first=_landmark_midpoint(landmarks, 33, 133, width, height),
                second=_landmark_midpoint(landmarks, 362, 263, width, height),
            )
        return TrackingResult(detected=True, eyes=eyes)

    def close(self):
        self.landmarker.close()

def _landmark_midpoint(landmarks, first_index, second_index, width, height):
    first = landmarks[first_index]
    second = landmarks[second_index]
    return Point2D(
        x=(first.x + second.x) * width / 2.0,
        y=(first.y + second.y) * height / 2.0,
    )
