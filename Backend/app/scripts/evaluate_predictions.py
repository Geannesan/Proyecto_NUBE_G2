"""Evalúa puntuaciones exportadas sin confundir confianza con rendimiento.

CSV requerido: media_type,axis,ground_truth,score
ground_truth: 1 sospechoso, 0 auténtico. score: probabilidad sospechosa 0..100.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _roc_auc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    positives = int(labels.sum())
    negatives = len(labels) - positives
    if not positives or not negatives:
        return None
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    # Promediar rangos empatados.
    for value in np.unique(scores):
        tied = np.flatnonzero(scores == value)
        ranks[tied] = float(np.mean(ranks[tied]))
    rank_sum = float(ranks[labels == 1].sum())
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def _eer(labels: np.ndarray, scores: np.ndarray) -> tuple[float | None, float | None]:
    if len(np.unique(labels)) < 2:
        return None, None
    best = None
    for threshold in np.unique(np.concatenate(([0.0], scores, [100.0]))):
        predicted = scores >= threshold
        fpr = _safe_div(float(np.sum(predicted & (labels == 0))), float(np.sum(labels == 0)))
        fnr = _safe_div(float(np.sum(~predicted & (labels == 1))), float(np.sum(labels == 1)))
        candidate = (abs(fpr - fnr), (fpr + fnr) / 2, float(threshold))
        if best is None or candidate < best:
            best = candidate
    return best[1], best[2]  # type: ignore[index]


def evaluate(rows: list[dict], threshold: float = 50.0) -> dict:
    labels = np.asarray([int(row["ground_truth"]) for row in rows], dtype=int)
    scores = np.asarray([float(row["score"]) for row in rows], dtype=float)
    probabilities = np.clip(scores / 100.0, 0.0, 1.0)
    predicted = scores >= threshold
    tp = int(np.sum(predicted & (labels == 1)))
    tn = int(np.sum(~predicted & (labels == 0)))
    fp = int(np.sum(predicted & (labels == 0)))
    fn = int(np.sum(~predicted & (labels == 1)))
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    specificity = _safe_div(tn, tn + fp)
    eer, eer_threshold = _eer(labels, scores)

    bins = []
    ece = 0.0
    for lower in range(0, 100, 10):
        mask = (scores >= lower) & (scores < lower + 10 if lower < 90 else scores <= 100)
        if not mask.any():
            continue
        predicted_rate = float(np.mean(probabilities[mask]))
        observed_rate = float(np.mean(labels[mask]))
        ece += float(np.mean(mask)) * abs(predicted_rate - observed_rate)
        bins.append({
            "range": [lower, lower + 10],
            "count": int(mask.sum()),
            "mean_score": round(predicted_rate * 100, 4),
            "observed_positive_rate": round(observed_rate * 100, 4),
        })

    return {
        "samples": len(rows),
        "threshold": threshold,
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "accuracy": round(_safe_div(tp + tn, len(rows)), 6),
        "precision": round(precision, 6),
        "recall_sensitivity": round(recall, 6),
        "specificity": round(specificity, 6),
        "f1": round(_safe_div(2 * precision * recall, precision + recall), 6),
        "false_positive_rate": round(1 - specificity, 6),
        "false_negative_rate": round(1 - recall, 6),
        "roc_auc": round(value, 6) if (value := _roc_auc(labels, scores)) is not None else None,
        "eer": round(eer, 6) if eer is not None else None,
        "eer_threshold": round(eer_threshold, 4) if eer_threshold is not None else None,
        "brier_score": round(float(np.mean((probabilities - labels) ** 2)), 6),
        "expected_calibration_error": round(ece, 6),
        "calibration_bins": bins,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, default=Path("calibration/metrics.json"))
    parser.add_argument("--threshold", type=float, default=50.0)
    args = parser.parse_args()

    with args.csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    required = {"media_type", "axis", "ground_truth", "score"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit(f"CSV vacío o faltan columnas: {sorted(required)}")

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["ground_truth"] not in {"0", "1"}:
            raise SystemExit("ground_truth solo admite 0 o 1")
        grouped[f"{row['media_type']}:{row['axis']}"] .append(row)

    payload = {
        "schema_version": "1.0",
        "warning": "Estas métricas solo son válidas para este dataset etiquetado.",
        "groups": {key: evaluate(items, args.threshold) for key, items in grouped.items()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
