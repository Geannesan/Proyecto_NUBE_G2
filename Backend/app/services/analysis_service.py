from pathlib import Path
from time import perf_counter
from typing import Literal

from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image
from sqlalchemy.orm import Session

from app.database.repositories import create_analysis
from app.detector.analyzer import build_analysis_response
from app.detector.audio_detector import analyze_audio
from app.detector.image_ai_detector import analyze_image_ai
from app.detector.image_deepfake_detector import (
    analyze_image_deepfake,
)
from app.detector.video_detector import analyze_video
from app.services.file_service import (
    SavedUpload,
    delete_saved_upload,
    save_upload,
)


MediaType = Literal["image", "audio", "video"]
DetectorType = Literal["ai", "deepfake"]


def normalize_detector_type(
    detector_type: str,
) -> DetectorType:
    value = detector_type.strip().lower()

    aliases = {
        "ai": "ai",
        "ia": "ai",
        "generated": "ai",
        "synthetic": "ai",
        "deepfake": "deepfake",
        "fake": "deepfake",
    }

    normalized = aliases.get(value)

    if normalized is None:
        raise ValueError(
            "detector_type debe ser 'ai' o 'deepfake'."
        )

    return normalized  # type: ignore[return-value]


def _run_image_detector(
    path: Path,
    detector_type: DetectorType,
):
    with Image.open(path) as image:
        image_copy = image.convert("RGB").copy()

    if detector_type == "ai":
        return analyze_image_ai(image_copy)

    return analyze_image_deepfake(image_copy)


def _run_audio_detector(path: Path):
    return analyze_audio(path)


def _run_video_detector(
    path: Path,
    detector_type: DetectorType,
):
    return analyze_video(
        path,
        detector_type=detector_type,
    )


async def analyze_upload(
    *,
    upload: UploadFile,
    media_type: MediaType,
    detector_type: str,
    db: Session,
) -> dict:
    normalized_detector = normalize_detector_type(
        detector_type
    )

    saved: SavedUpload | None = None
    started_at = perf_counter()

    try:
        saved = await save_upload(
            upload,
            media_type,
        )

        if media_type == "image":
            result = await run_in_threadpool(
                _run_image_detector,
                saved.path,
                normalized_detector,
            )

        elif media_type == "audio":
            result = await run_in_threadpool(
                _run_audio_detector,
                saved.path,
            )

        elif media_type == "video":
            result = await run_in_threadpool(
                _run_video_detector,
                saved.path,
                normalized_detector,
            )

        else:
            raise ValueError(
                f"Tipo multimedia no soportado: {media_type}"
            )

        processing_time_ms = round(
            (perf_counter() - started_at) * 1000
        )

        record = create_analysis(
            db,
            original_filename=saved.original_filename,
            stored_filename=saved.stored_filename,
            file_path=str(saved.path),
            content_type=saved.content_type,
            size_bytes=saved.size_bytes,
            media_type=media_type,
            detector_type=normalized_detector,
            prediction=result.prediction,
            confidence=result.confidence,
            probabilities=result.probabilities,
            evidence=result.evidence,
            model_name=result.model_name,
            processing_time_ms=processing_time_ms,
            status="completed",
            error_message=None,
        )

        return build_analysis_response(
            result=result,
            media_type=media_type,
            detector_type=normalized_detector,
            filename=saved.original_filename,
            processing_time_ms=processing_time_ms,
            analysis_id=record.id,
            created_at=record.created_at.isoformat(),
        )

    except Exception:
        delete_saved_upload(saved)
        raise
