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
