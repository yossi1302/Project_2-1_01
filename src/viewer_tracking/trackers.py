from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import cv2
import numpy as np

from .models import EyePair, Point2D, TrackingResult


class Tracker(ABC):
    name: str

    @abstractmethod
    def track(self, frame_bgr: np.ndarray, timestamp_ms: int) -> TrackingResult:
        raise NotImplementedError

    def close(self) -> None:
        return None


class HaarTracker(Tracker):
    name = "haar"

    def __init__(self, model_directory: Path) -> None:
        face_path = model_directory / "haarcascade_frontalface_default.xml"
        eyes_path = model_directory / "haarcascade_eye_tree_eyeglasses.xml"
        if not face_path.exists() or not eyes_path.exists():
            raise FileNotFoundError(
                "Haar cascade files are missing. Run 'viewer-tracking download-models'."
            )
        self._face = cv2.CascadeClassifier(str(face_path))
        self._eyes = cv2.CascadeClassifier(str(eyes_path))
        if self._face.empty() or self._eyes.empty():
            raise RuntimeError("OpenCV Haar cascade files could not be loaded")

    def track(self, frame_bgr: np.ndarray, timestamp_ms: int) -> TrackingResult:
        del timestamp_ms
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self._face.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) == 0:
            return TrackingResult.missed()

        x, y, width, height = max(faces, key=lambda box: int(box[2]) * int(box[3]))
        upper_face = gray[y : y + int(height * 0.65), x : x + width]
        candidates = self._eyes.detectMultiScale(
            upper_face,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(15, 15),
        )
        pair = _select_eye_pair(candidates, x_offset=x, y_offset=y)
        return TrackingResult(detected=True, eyes=pair) if pair else TrackingResult.missed()


class YuNetTracker(Tracker):
    name = "yunet"

    def __init__(self, model_path: Path, score_threshold: float = 0.8) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"YuNet model not found: {model_path}")
        self._detector = cv2.FaceDetectorYN.create(
            str(model_path),
            "",
            (320, 320),
            score_threshold,
            0.3,
            5000,
        )

    def track(self, frame_bgr: np.ndarray, timestamp_ms: int) -> TrackingResult:
        del timestamp_ms
        height, width = frame_bgr.shape[:2]
        self._detector.setInputSize((width, height))
        _, faces = self._detector.detect(frame_bgr)
        if faces is None or len(faces) == 0:
            return TrackingResult.missed()

        face = max(faces, key=lambda row: float(row[2] * row[3]))
        eyes = EyePair(
            first=Point2D(float(face[4]), float(face[5])),
            second=Point2D(float(face[6]), float(face[7])),
        )
        return TrackingResult(detected=True, eyes=eyes, confidence=float(face[14]))


class MediaPipeTracker(Tracker):
    name = "mediapipe"

    def __init__(self, model_path: Path) -> None:
        if not model_path.exists():
            raise FileNotFoundError(f"MediaPipe model not found: {model_path}")
        import mediapipe as mp

        self._mp = mp
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
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    def track(self, frame_bgr: np.ndarray, timestamp_ms: int) -> TrackingResult:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.face_landmarks:
            return TrackingResult.missed()

        landmarks = result.face_landmarks[0]
        height, width = frame_bgr.shape[:2]
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

    def close(self) -> None:
        self._landmarker.close()


def create_tracker(name: str, model_directory: Path) -> Tracker:
    if name == "haar":
        return HaarTracker(model_directory)
    if name == "yunet":
        return YuNetTracker(model_directory / "face_detection_yunet_2023mar.onnx")
    if name == "mediapipe":
        return MediaPipeTracker(model_directory / "face_landmarker.task")
    raise ValueError(f"Unknown tracking method: {name}")


def _select_eye_pair(
    detections: np.ndarray,
    x_offset: int,
    y_offset: int,
) -> EyePair | None:
    centres = [
        Point2D(x_offset + x + width / 2.0, y_offset + y + height / 2.0)
        for x, y, width, height in detections
    ]
    best: tuple[float, EyePair] | None = None
    for index, first in enumerate(centres):
        for second in centres[index + 1 :]:
            horizontal_distance = abs(second.x - first.x)
            vertical_distance = abs(second.y - first.y)
            if horizontal_distance < 20 or vertical_distance > horizontal_distance * 0.35:
                continue
            pair = EyePair(first, second)
            score = horizontal_distance - 2.0 * vertical_distance
            if best is None or score > best[0]:
                best = score, pair
    return best[1] if best else None


def _landmark_midpoint(
    landmarks: list,
    first_index: int,
    second_index: int,
    width: int,
    height: int,
) -> Point2D:
    first = landmarks[first_index]
    second = landmarks[second_index]
    return Point2D(
        x=(first.x + second.x) * width / 2.0,
        y=(first.y + second.y) * height / 2.0,
    )
