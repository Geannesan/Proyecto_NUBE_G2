"""Registra pares original/editado revisados sin duplicar hashes."""

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("training_data"))
    parser.add_argument("--pair", action="append", required=True, help="EDITADA::ORIGINAL")
    parser.add_argument("--source", default="user_confirmed_ai_edited_batch")
    args = parser.parse_args()
    manifest = args.data_dir / "manifest.jsonl"
    entries = [
        json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ] if manifest.exists() else []
    known = {
        value for entry in entries
        for value in (entry.get("edited_sha256"), entry.get("original_sha256"), entry.get("reference_sha256"))
        if value
    }
    registered = []
    for specification in args.pair:
        edited_text, original_text = specification.split("::", 1)
        edited, original = Path(edited_text), Path(original_text)
        edited_hash, original_hash = digest(edited), digest(original)
        if edited_hash == original_hash:
            raise SystemExit(f"El par contiene el mismo archivo: {edited.name}")
        if edited_hash in known or original_hash in known:
            print(json.dumps({"status": "skipped_known_hash", "edited": edited.name, "original": original.name}, ensure_ascii=False))
            continue
        pair_id = uuid4().hex
        pair_dir = args.data_dir / "pairs" / pair_id
        pair_dir.mkdir(parents=True)
        edited_target = pair_dir / f"edited{edited.suffix.lower()}"
        original_target = pair_dir / f"original{original.suffix.lower()}"
        shutil.copy2(edited, edited_target)
        shutil.copy2(original, original_target)
        entry = {
            "schema_version": "1.0", "pair_id": pair_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "label": "AI_EDITED", "label_source": args.source,
            "review_status": "approved",
            "review_basis": "Par original/editado confirmado por el usuario para entrenamiento AI_EDITED.",
            "edited_sha256": edited_hash, "original_sha256": original_hash,
            "edited_path": str(edited_target.relative_to(args.data_dir)),
            "original_path": str(original_target.relative_to(args.data_dir)),
            "edited_filename": edited.name, "original_filename": original.name,
        }
        entries.append(entry)
        known.update((edited_hash, original_hash))
        registered.append(entry)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in entries), encoding="utf-8")
    print(json.dumps({"registered": len(registered), "pairs_total": len(entries)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
