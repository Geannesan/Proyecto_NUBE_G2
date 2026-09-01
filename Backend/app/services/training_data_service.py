import json
import hashlib
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services.file_service import SavedUpload


TRAINING_DATA_DIR = Path(os.getenv("TRAINING_DATA_DIR", "training_data")).resolve()
_manifest_lock = threading.Lock()


def find_reviewed_sample(path: Path) -> dict | None:
    """Busca una coincidencia binaria exacta en el corpus ya revisado."""
    manifest = TRAINING_DATA_DIR / "manifest.jsonl"
    if not manifest.exists():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with _manifest_lock:
        entries = [
            json.loads(line)
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    for entry in entries:
        if entry.get("review_status") != "approved":
            continue
        sample_role = None
        if entry.get("edited_sha256") == digest:
            sample_role = "edited"
        elif entry.get("original_sha256", entry.get("reference_sha256")) == digest:
            sample_role = "original"
        if sample_role:
            return {
                "match": "sha256_exact",
                "sha256": digest,
                "pair_id": entry.get("pair_id"),
                "label": entry.get("label"),
                "sample_role": sample_role,
                "label_source": entry.get("label_source"),
                "review_basis": entry.get("review_basis"),
                "metric_kind": "known_sample_lookup_not_model_probability",
            }
    return None


def register_ai_edited_pair(
    *, edited: SavedUpload, original: SavedUpload, comparison: dict
) -> dict:
    """Registra un par consentido sin convertirlo automáticamente en modelo."""
    pair_id = uuid4().hex
    pair_dir = TRAINING_DATA_DIR / "pairs" / pair_id
    pair_dir.mkdir(parents=True, exist_ok=False)
    edited_suffix = edited.path.suffix.lower() or ".bin"
    original_suffix = original.path.suffix.lower() or ".bin"
    edited_target = pair_dir / f"edited{edited_suffix}"
    original_target = pair_dir / f"original{original_suffix}"
    shutil.copy2(edited.path, edited_target)
    shutil.copy2(original.path, original_target)

    entry = {
        "schema_version": "1.0",
        "pair_id": pair_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label": "AI_EDITED",
        "label_source": "user_declared_with_original_reference",
        "review_status": "pending_human_review",
        "edited_sha256": hashlib.sha256(edited.path.read_bytes()).hexdigest(),
        "edited_path": str(edited_target.relative_to(TRAINING_DATA_DIR)),
        "original_path": str(original_target.relative_to(TRAINING_DATA_DIR)),
        "edited_filename": edited.original_filename,
        "original_filename": original.original_filename,
        "reference_sha256": comparison.get("reference_sha256"),
        "comparison": {
            key: comparison.get(key)
            for key in (
                "feature_matches", "overlap_percent", "mean_pixel_difference",
                "changed_area_over_25_percent", "changed_area_over_50_percent",
            )
        },
    }
    manifest = TRAINING_DATA_DIR / "manifest.jsonl"
    with _manifest_lock:
        with manifest.open("a", encoding="utf-8") as output:
            output.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {
        "pair_id": pair_id,
        "status": entry["review_status"],
        "label": entry["label"],
        "message": "Par guardado para revisión; todavía no modifica el modelo activo.",
    }
