from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def create_plots(summary_csv: Path, output_directory: Path) -> tuple[Path, Path]:
    with summary_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No result rows found in {summary_csv}")

    output_directory.mkdir(parents=True, exist_ok=True)
    detection_path = output_directory / "detection_success.pdf"
    latency_path = output_directory / "latency_p95.pdf"
    _grouped_bar(
        rows,
        value_key="detection_success_pct",
        ylabel="Detected frames (%)",
        output=detection_path,
        limit=(0, 100),
    )
    _grouped_bar(
        rows,
        value_key="latency_p95_ms",
        ylabel="P95 processing latency (ms)",
        output=latency_path,
    )
    return detection_path, latency_path


def _grouped_bar(
    rows: list[dict[str, str]],
    value_key: str,
    ylabel: str,
    output: Path,
    limit: tuple[float, float] | None = None,
) -> None:
    grouped: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        grouped[row["condition"]][row["method"]] = float(row[value_key])
    conditions = list(grouped)
    methods = sorted({method for values in grouped.values() for method in values})
    width = 0.8 / len(methods)
    positions = list(range(len(conditions)))

    figure, axis = plt.subplots(figsize=(7.0, 3.0))
    for index, method in enumerate(methods):
        offset = (index - (len(methods) - 1) / 2.0) * width
        axis.bar(
            [position + offset for position in positions],
            [grouped[condition].get(method, 0.0) for condition in conditions],
            width=width,
            label=method,
        )
    axis.set_ylabel(ylabel)
    axis.set_xticks(positions, conditions, rotation=25, ha="right")
    if limit:
        axis.set_ylim(*limit)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False, ncol=len(methods))
    figure.tight_layout()
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
