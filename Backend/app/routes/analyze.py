import logging
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.analysis_service import analyze_upload

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Compatibility"],
)


async def _run(
    *,
    file: UploadFile,
    media_type: str,
    detector_type: str,
    db: Session,
):
    try:
        return await analyze_upload(
            upload=file,
            media_type=media_type,  # type: ignore[arg-type]
            detector_type=detector_type,
            db=db,
        )

    except Exception as error:
        logger.exception(
            "Error procesando %s con detector %s",
            media_type,
            detector_type,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "No fue posible completar el análisis. "
                f"Detalle: {type(error).__name__}: {error}"
            ),
        ) from error


@router.post("/analyze")
async def legacy_image_ai(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await _run(
        file=file,
        media_type="image",
        detector_type="ai",
        db=db,
    )


@router.post("/analyze/image/deepfake")
async def legacy_image_deepfake(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await _run(
        file=file,
        media_type="image",
        detector_type="deepfake",
        db=db,
    )


@router.post("/analyze/audio")
async def legacy_audio_ai(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await _run(
        file=file,
        media_type="audio",
        detector_type="ai",
        db=db,
    )


@router.post("/analyze/audio/deepfake")
async def legacy_audio_deepfake(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await _run(
        file=file,
        media_type="audio",
        detector_type="deepfake",
        db=db,
    )


@router.post("/analyze/video")
async def legacy_video_ai(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await _run(
        file=file,
        media_type="video",
        detector_type="ai",
        db=db,
    )


@router.post("/analyze/video/deepfake")
async def legacy_video_deepfake(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await _run(
        file=file,
        media_type="video",
        detector_type="deepfake",
        db=db,
    )
