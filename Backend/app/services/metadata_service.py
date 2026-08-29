import json
import subprocess
from pathlib import Path

from PIL import ExifTags, Image


def _image_metadata(path: Path) -> dict:
    with Image.open(path) as image:
        exif = {
            ExifTags.TAGS.get(key, str(key)): str(value)
            for key, value in image.getexif().items()
        }
        return {
            "format": image.format,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "exif_present": bool(exif),
            "exif": exif,
            "software": exif.get("Software"),
            "capture_datetime": exif.get("DateTimeOriginal", exif.get("DateTime")),
        }


def _ffprobe_metadata(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-show_format", "-show_streams",
        "-of", "json", str(path),
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return {"status": "unavailable", "reason": type(error).__name__}
    if completed.returncode != 0:
        return {"status": "unreadable", "reason": completed.stderr[-300:]}
    payload = json.loads(completed.stdout)
    streams = []
    for stream in payload.get("streams", []):
        streams.append({
            key: stream.get(key)
            for key in (
                "index", "codec_type", "codec_name", "profile", "width", "height",
                "sample_rate", "channels", "duration", "bit_rate", "avg_frame_rate",
            )
            if stream.get(key) is not None
        })
    media_format = payload.get("format", {})
    return {
        "status": "available",
        "format_name": media_format.get("format_name"),
        "duration": media_format.get("duration"),
        "size": media_format.get("size"),
        "bit_rate": media_format.get("bit_rate"),
        "tags": media_format.get("tags", {}),
        "streams": streams,
    }


def inspect_technical_metadata(path: str | Path, media_type: str) -> dict:
    media_path = Path(path)
    try:
        return _image_metadata(media_path) if media_type == "image" else _ffprobe_metadata(media_path)
    except Exception as error:
        return {"status": "unreadable", "reason": type(error).__name__}
