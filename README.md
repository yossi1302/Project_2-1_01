# Project 2.1: parallax viewer tracking

This repository contains phase-one component tests for a webcam-driven parallax interface. The current comparison is deliberately limited to viewer-position tracking. It evaluates three ways to locate the midpoint between a viewer's eyes:

- OpenCV Haar face and eye cascades
- OpenCV YuNet face detection with eye landmarks
- MediaPipe Face Landmarker with iris landmarks

The original 3D-library exploration remains in `Library analysis/` and is outside this comparison.

## Reference machine

The controlled measurements target a 13-inch 2020 MacBook Pro with Apple M1, 16 GB RAM, macOS 26.5.2, and its built-in 720p camera.

## Setup

Use Python 3.12 on Apple Silicon. MediaPipe 1.0.1 aborts during Face Landmarker initialisation on the reference Mac, while the pinned 0.10.21 wheel passes the same smoke test. Python 3.13 cannot install that working wheel.

```bash
python3.12 -m venv .venv312
.venv312/bin/python -m pip install --upgrade pip
.venv312/bin/python -m pip install -r requirements-lock.txt
.venv312/bin/python -m pip install -e . --no-deps
.venv312/bin/viewer-tracking download-models
```

The last command downloads model files from the official OpenCV and MediaPipe sources and records their URLs and SHA-256 hashes in `models/manifest.json`.

## Record the controlled inputs

The experiment definition is in `config/experiment.toml`. No interpupillary-distance measurement and no separate condition files are required. Mark the configured reference distance (600 mm by default), then start one guided recording. The preview displays each instruction and a countdown. Yellow preparation segments allow time to change lighting, put on glasses, or return to the starting pose; those frames are excluded from testing. Green calibration and test segments are retained.

```bash
.venv312/bin/viewer-tracking record
```

The approximately 170-second session is saved as `data/private/experiment.mp4`, which Git ignores because it contains an identifiable face. Its opening five seconds are the shared calibration segment. The eight 15-second test segments are cut logically from the same file; preparation frames are not benchmarked.

A known reference distance is still needed because one ordinary webcam cannot recover absolute millimetres from pixels without one physical scale reference. Change `calibration.reference_distance_mm` if another marked distance is more convenient; this is a camera setup value, not a personal biometric measurement.

## Run the comparison

```bash
.venv312/bin/viewer-tracking benchmark
.venv312/bin/viewer-tracking plot
.venv312/bin/viewer-tracking build-report-data
```

The benchmark calibrates each method from the same opening segment, excludes it and all preparation periods from reported measurements, and processes every test segment three times. It writes the learned baselines, per-frame measurements, and aggregate results under `results/latest/`. The plot command creates PDF figures for the report. The final command fills the report table and writes the selection produced by the predefined gates and weights.

The reference Mac currently maps its built-in camera to index 1 because OBS Virtual Camera occupies index 0. If the preview shows OBS or the wrong device, select another camera without editing the configuration:

```bash
.venv312/bin/viewer-tracking record --camera-index 1
```

Running the record command again replaces the previous guided session, so a failed OBS recording does not need to be deleted manually.

## Reported measures

- Detection success is the percentage of frames with two valid eye centres.
- Tracking latency covers one method call on an already decoded frame. Camera and rendering time are excluded.
- Stationary jitter is the sample standard deviation of the estimated position.
- Positional error is reported only for conditions with a measured reference position.

Do not report experimental values until `results/latest/summary.csv` has been produced on the reference machine. Commit the CSV files and plots needed to reproduce every table and figure, but do not commit the source videos.

## Live parallax scene

`viewer-tracking parallax` opens a Flet window with a Panda3D room drawn as if the display were a window into it. The virtual camera follows the tracked eye midpoint through an off-axis projection, so moving your head reveals the side walls, and the nearest cubes appear in front of the screen. The sidebar shows the mirrored camera preview with the detected eyes, the smoothed position, depth, tracking latency, detection rate, and camera and render frame rates.

```bash
.venv312/bin/python -m pip install -e ".[parallax]"
.venv312/bin/viewer-tracking parallax --camera-index 1
```

MediaPipe is the default method. The depth baseline for each method comes from `results/latest/calibration.csv`. If that file is missing, the app uses a typical 63 mm eye separation until you sit at the reference distance and press **Calibrate**. The display defaults describe the reference MacBook Pro. For another screen, pass `--screen-width-mm`, `--screen-height-mm`, and `--camera-above-screen-mm`. Use `--video data/private/experiment.mp4` to replay a recording in a loop instead of using the camera.

On macOS, the first launch requests camera access. The app keeps retrying until access is granted, so the prompt does not require a restart.

## Tests

```bash
.venv312/bin/python -m pytest
.venv312/bin/ruff check .
```
