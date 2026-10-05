import mediapipe as mp
import cv2
import numpy as np

# This was mostly copied straight from the old one, I tried to test it,
# didn't run on my laptop, nothing works and I am very sad :(
#       - stefan
class Tracker:
    def __init__(self):
        model_path = "./model/face_landmarker.task"
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(model_path),
                delegate=mp.tasks.BaseOptions.Delegate.CPU,
            ),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    def find(self, frame, timestamp):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect_for_video(image, timestamp)
        if not result.face_landmarks:
            return TrackingResult.missed()

        landmarks = result.face_landmarks[0]
        height, width = frame.shape[:2]
        if len(landmarks) >= 478:
            first_index, second_index = 468, 473
            first = landmarks[first_index]
            second = landmarks[second_index]
            eyes = EyePair(
                first=Point2D(first.x * width, first.y * height),
                second=Point2D(second.x * width, second.y * height),
            )
        else:
            eyes = EyePair(
                first=_landmark_midpoint(landmarks, 33, 133, width, height),
                second=_landmark_midpoint(landmarks, 362, 263, width, height),
            )
        return TrackingResult(detected=True, eyes=eyes)

