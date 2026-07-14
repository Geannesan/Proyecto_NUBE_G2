import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


UPLOAD_DIR = Path(
    os.getenv("UPLOAD_DIR", "uploads")
).resolve()

MAX_UPLOAD_MB = int(
    os.getenv("MAX_UPLOAD_MB", "200")
)

MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "image": {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
    },
    "audio": {
        ".wav",
        ".mp3",
        ".flac",
        ".ogg",
        ".m4a",
        ".aac",
    },
    "video": {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".webm",
        ".m4v",
    },
}


@dataclass(slots=True)
class SavedUpload:
    original_filename: str
    stored_filename: str
    path: Path
    content_type: str | None
    size_bytes: int


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        filename,
    )

    return cleaned[:180] or "archivo"


def validate_upload_metadata(
    upload: UploadFile,
    media_type: str,
) -> None:
    media_type = media_type.lower()

    if media_type not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Tipo multimedia no soportado: {media_type}"
        )

    filename = upload.filename or "archivo"
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS[media_type]:
        allowed = ", ".join(
            sorted(ALLOWED_EXTENSIONS[media_type])
        )

        raise ValueError(
            f"Extensión no permitida para {media_type}. "
            f"Permitidas: {allowed}"
        )

    if (
        upload.content_type
        and not upload.content_type.startswith(
            f"{media_type}/"
        )
    ):
        raise ValueError(
            f"El archivo debe ser de tipo {media_type}."
        )


async def save_upload(
    upload: UploadFile,
    media_type: str,
) -> SavedUpload:
    validate_upload_metadata(
        upload,
        media_type,
    )

    media_dir = UPLOAD_DIR / media_type
    media_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    original_filename = (
        upload.filename or "archivo"
    )

    stored_filename = (
        f"{uuid4().hex}_"
        f"{_safe_filename(original_filename)}"
    )

    destination = media_dir / stored_filename
    total_bytes = 0

    try:
        with destination.open("wb") as output:
            while chunk := await upload.read(
                1024 * 1024
            ):
                total_bytes += len(chunk)

                if total_bytes > MAX_UPLOAD_BYTES:
                    raise ValueError(
                        f"El archivo supera el límite "
                        f"de {MAX_UPLOAD_MB} MB."
                    )

                output.write(chunk)

    except Exception:
        destination.unlink(missing_ok=True)
        raise

    finally:
        await upload.close()

    return SavedUpload(
        original_filename=original_filename,
        stored_filename=stored_filename,
        path=destination,
        content_type=upload.content_type,
        size_bytes=total_bytes,
    )


def delete_saved_upload(
    saved_upload: SavedUpload | None,
) -> None:
    if saved_upload is not None:
        saved_upload.path.unlink(
            missing_ok=True
        )
