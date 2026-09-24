# Model files

Run `viewer-tracking download-models` after installing the project. The command downloads:

- OpenCV's frontal-face and eye cascade files from the official OpenCV repository.
- OpenCV YuNet from the official OpenCV Zoo repository.
- MediaPipe Face Landmarker from Google's official model storage.

The binary files are excluded from Git. `models/manifest.json` records their source URLs and SHA-256 checksums after download.
