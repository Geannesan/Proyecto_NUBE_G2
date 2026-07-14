from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.repositories import (
    analysis_to_dict,
    get_analysis,
    list_analyses,
)


router = APIRouter(
    prefix="/api/v1/history",
    tags=["History"],
)


@router.get("")
def get_history(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    media_type: str | None = Query(default=None),
    detector_type: str | None = Query(default=None),
    prediction: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    records = list_analyses(
        db,
        offset=offset,
        limit=limit,
        media_type=media_type,
        detector_type=detector_type,
        prediction=prediction,
    )

    return {
        "offset": offset,
        "limit": limit,
        "items": [
            analysis_to_dict(record)
            for record in records
        ],
    }


@router.get("/{analysis_id}")
def get_history_item(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    record = get_analysis(
        db,
        analysis_id,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Análisis no encontrado.",
        )

    return analysis_to_dict(
        record,
        include_file_path=True,
    )
