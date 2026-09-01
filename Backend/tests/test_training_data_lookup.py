import hashlib
import json

from app.services import training_data_service


def test_reviewed_pair_recognizes_original_and_edited_roles(tmp_path, monkeypatch):
    original = tmp_path / "original.jpeg"
    edited = tmp_path / "edited.jpeg"
    original.write_bytes(b"authentic-sample")
    edited.write_bytes(b"edited-sample")
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps({
        "pair_id": "pair-1",
        "label": "DEEPFAKE_EDITED",
        "review_status": "approved",
        "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "edited_sha256": hashlib.sha256(edited.read_bytes()).hexdigest(),
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(training_data_service, "TRAINING_DATA_DIR", tmp_path)

    assert training_data_service.find_reviewed_sample(original)["sample_role"] == "original"
    assert training_data_service.find_reviewed_sample(edited)["sample_role"] == "edited"


def test_incremental_confirmation_does_not_approve_unconfirmed_original(tmp_path, monkeypatch):
    edited = tmp_path / "edited.jpeg"
    original = tmp_path / "original.jpeg"
    edited.write_bytes(b"confirmed-edited")
    original.write_bytes(b"unconfirmed-original")
    (tmp_path / "manifest.jsonl").write_text(json.dumps({
        "pair_id": "pending-pair",
        "review_status": "pending_pair_confirmation",
        "edited_review_status": "approved",
        "edited_sha256": hashlib.sha256(edited.read_bytes()).hexdigest(),
        "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(training_data_service, "TRAINING_DATA_DIR", tmp_path)

    assert training_data_service.find_reviewed_sample(edited)["sample_role"] == "edited"
    assert training_data_service.find_reviewed_sample(original) is None


def test_completed_incremental_pair_exposes_both_confirmed_roles(tmp_path, monkeypatch):
    edited = tmp_path / "edited.jpeg"
    original = tmp_path / "original.jpeg"
    edited.write_bytes(b"confirmed-edited")
    original.write_bytes(b"confirmed-original")
    (tmp_path / "manifest.jsonl").write_text(json.dumps({
        "pair_id": "completed-pair",
        "review_status": "approved",
        "edited_review_status": "approved",
        "original_review_status": "approved",
        "edited_sha256": hashlib.sha256(edited.read_bytes()).hexdigest(),
        "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(training_data_service, "TRAINING_DATA_DIR", tmp_path)

    assert training_data_service.find_reviewed_sample(edited)["sample_role"] == "edited"
    assert training_data_service.find_reviewed_sample(original)["sample_role"] == "original"
