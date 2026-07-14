from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.analysis_service import analyze_upload


router = APIRouter(
    prefix="/api/v1/audio",
    tags=["Audio"],
)


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, ValueError):
        return HTTPException(
            status_code=400,
            detail=str(error),
        )

    return HTTPException(
        status_code=500,
        detail=(
            "No fue posible analizar el audio. "
            f"Detalle: {error}"
        ),
    )


@router.post("/analyze")
async def analyze_audio_route(
    file: UploadFile = File(...),
    detector_type: str = Form("deepfake"),
    db: Session = Depends(get_db),
):
    try:
        return await analyze_upload(
            upload=file,
            media_type="audio",
            detector_type=detector_type,
            db=db,
        )
    except Exception as error:
        raise _http_error(error) from error
