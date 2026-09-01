"""Confirma incrementalmente un único rol sin aprobar una pareja inferida."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("training_data"))
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--role", choices=("edited", "original"), required=True)
    args = parser.parse_args()
    digest = hashlib.sha256(args.file.read_bytes()).hexdigest()
    manifest = args.data_dir / "manifest.jsonl"
    entries = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    matched = None
    for entry in entries:
        key = f"{args.role}_sha256"
        if entry.get(key) == digest:
            entry[f"{args.role}_review_status"] = "approved"
            other_role = "original" if args.role == "edited" else "edited"
            if entry.get(f"{other_role}_review_status") == "approved":
                entry["review_status"] = "approved"
            else:
                entry["review_status"] = "pending_pair_confirmation"
            entry["label_source"] = "user_confirmed_incrementally"
            entry["review_basis"] = f"El usuario confirmó explícitamente el rol {args.role} de este archivo."
            entry.pop("invalidation_reason", None)
            matched = entry
            break
    if matched is None:
        raise SystemExit("El hash no existe todavía en el corpus pendiente para ese rol.")
    manifest.write_text("".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries), encoding="utf-8")
    print(json.dumps({"pair_id": matched["pair_id"], "role": args.role, "sha256": digest, "pair_status": matched["review_status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
