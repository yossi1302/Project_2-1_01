from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config

METHODS = ("haar", "yunet", "mediapipe")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="viewer-tracking",
        description="Record and benchmark viewer-position tracking methods.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download-models", help="Download official model files")
    download.add_argument("--models", type=Path, default=Path("models"))

    record = subparsers.add_parser("record", help="Record one guided experiment session")
    record.add_argument("--config", type=Path, default=Path("config/experiment.toml"))
    record.add_argument(
        "--camera-index",
        type=int,
        help="Override the configured OpenCV camera index",
    )

    benchmark = subparsers.add_parser("benchmark", help="Run all methods on recorded videos")
    benchmark.add_argument("--config", type=Path, default=Path("config/experiment.toml"))
    benchmark.add_argument("--models", type=Path, default=Path("models"))
    benchmark.add_argument("--output", type=Path, default=Path("results/latest"))
    benchmark.add_argument(
        "--methods",
        nargs="+",
        choices=METHODS,
        default=list(METHODS),
    )

    plots = subparsers.add_parser("plot", help="Create report plots from summary.csv")
    plots.add_argument("--summary", type=Path, default=Path("results/latest/summary.csv"))
    plots.add_argument("--output", type=Path, default=Path("report/figures"))

    report = subparsers.add_parser(
        "build-report-data",
        help="Create the LaTeX results fragment and component selection",
    )
    report.add_argument("--summary", type=Path, default=Path("results/latest/summary.csv"))
    report.add_argument("--output", type=Path, default=Path("report/generated/results.tex"))

    parallax = subparsers.add_parser(
        "parallax",
        help="Open the live parallax scene driven by the webcam",
    )
    parallax.add_argument("--config", type=Path, default=Path("config/experiment.toml"))
    parallax.add_argument("--models", type=Path, default=Path("models"))
    parallax.add_argument(
        "--calibration",
        type=Path,
        default=Path("results/latest/calibration.csv"),
        help="Benchmark calibration file with per-method eye-separation baselines",
    )
    parallax.add_argument(
        "--camera-index",
        type=int,
        help="Override the configured OpenCV camera index",
    )
    parallax.add_argument(
        "--video",
        type=Path,
        help="Replay a recorded video in a loop instead of using the camera",
    )
    parallax.add_argument("--method", choices=METHODS, default="mediapipe")
    parallax.add_argument(
        "--screen-width-mm",
        type=float,
        default=286.0,
        help="Visible width of the display",
    )
    parallax.add_argument(
        "--screen-height-mm",
        type=float,
        default=179.0,
        help="Visible height of the display",
    )
    parallax.add_argument(
        "--camera-above-screen-mm",
        type=float,
        default=8.0,
        help="Distance from the top edge of the display up to the camera lens",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "download-models":
        from .downloads import download_models

        path = download_models(args.models)
        print(f"Model manifest written to {path}")
        return 0
    if args.command == "record":
        from .recording import record_session

        config = load_config(args.config)
        path = record_session(
            config,
            camera_index=args.camera_index,
        )
        print(f"Recording written to {path}")
        return 0
    if args.command == "benchmark":
        from .experiment import run_experiment

        config = load_config(args.config)
        calibration_path, frame_path, summary_path = run_experiment(
            config,
            args.models,
            args.output,
            tuple(args.methods),
        )
        print(f"Calibration data written to {calibration_path}")
        print(f"Frame measurements written to {frame_path}")
        print(f"Summary written to {summary_path}")
        return 0
    if args.command == "plot":
        from .plotting import create_plots

        paths = create_plots(args.summary, args.output)
        print("Plots written to " + ", ".join(map(str, paths)))
        return 0
    if args.command == "build-report-data":
        from .reporting import build_report_fragment

        path = build_report_fragment(args.summary, args.output)
        print(f"Report data written to {path}")
        return 0
    if args.command == "parallax":
        from .gui import run_gui
        from .live import ScreenGeometry

        config = load_config(args.config)
        run_gui(
            config,
            model_directory=args.models,
            calibration_path=args.calibration,
            source=args.video
            or (args.camera_index if args.camera_index is not None else config.camera_index),
            method=args.method,
            screen=ScreenGeometry(
                width_mm=args.screen_width_mm,
                height_mm=args.screen_height_mm,
                camera_above_top_mm=args.camera_above_screen_mm,
            ),
        )
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
