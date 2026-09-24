from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

MODEL_URLS = {
    "haarcascade_frontalface_default.xml": (
        "https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/"
        "haarcascade_frontalface_default.xml"
    ),
    "haarcascade_eye_tree_eyeglasses.xml": (
        "https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/"
        "haarcascade_eye_tree_eyeglasses.xml"
    ),
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
        "face_detection_yunet_2023mar.onnx"
    ),
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    ),
}


def download_models(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, str | int]] = {}
    for filename, url in MODEL_URLS.items():
        destination = directory / filename
        if not destination.exists():
            print(f"Downloading {filename}...")
            _download(url, destination)
        manifest[filename] = {
            "url": url,
            "sha256": _sha256(destination),
            "bytes": destination.stat().st_size,
        }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _download(url: str, destination: Path) -> None:
    partial = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
