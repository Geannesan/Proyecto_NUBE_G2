from pathlib import Path

from PIL import Image

from app.services.metadata_service import inspect_technical_metadata


def test_image_metadata_is_extracted(tmp_path: Path):
    path = tmp_path / "sample.png"
    Image.new("RGB", (32, 24), "white").save(path)
    metadata = inspect_technical_metadata(path, "image")
    assert metadata["format"] == "PNG"
    assert metadata["width"] == 32
    assert metadata["height"] == 24
    assert metadata["face_detection_status"] == "executed"
    assert metadata["faces_detected"] == 0
    consistency = metadata["forensic_metadata"]["consistency"]
    assert consistency["temporal_status"] == "no_declared_conflict"
    assert consistency["temporal_dates_available"] == 0
    assert consistency["temporal_coverage_percent"] == 0
    temporal_finding = next(
        item for item in metadata["forensic_metadata"]["findings"]
        if item["check"] == "Coherencia temporal declarada"
    )
    assert temporal_finding["status"] == "observed"
