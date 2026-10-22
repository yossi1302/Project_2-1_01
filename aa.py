import mediapipe as mp
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "face_landmarker.task")

if __name__ == "__main__":
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path=MODEL_PATH,
        ),
    )
    landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

