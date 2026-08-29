import json
import os
from pathlib import Path


VALIDATION_METRICS_PATH = Path(
    os.getenv("VALIDATION_METRICS_PATH", "calibration/metrics.json")
).resolve()


def load_validation_report() -> dict | None:
    if not VALIDATION_METRICS_PATH.is_file():
        return None
    try:
        payload = json.loads(VALIDATION_METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload.get("groups"), dict) else None


def get_axis_validation(media_type: str, axis: str) -> dict | None:
    report = load_validation_report()
    if report is None:
        return None
    metrics = report["groups"].get(f"{media_type}:{axis}")
    return metrics if isinstance(metrics, dict) else None
