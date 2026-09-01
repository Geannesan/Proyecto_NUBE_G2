"""Desactiva de forma reversible un lote cuya dirección de etiquetas no fue confirmada."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("training_data"))
    parser.add_argument("--label-source", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    manifest = args.data_dir / "manifest.jsonl"
    entries = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    changed = 0
    for entry in entries:
        if entry.get("label_source") == args.label_source:
            entry["review_status"] = "pending_label_confirmation"
            entry["invalidation_reason"] = args.reason
            changed += 1
    manifest.write_text("".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries), encoding="utf-8")
    print(json.dumps({"invalidated": changed, "label_source": args.label_source}, ensure_ascii=False))


if __name__ == "__main__":
    main()
