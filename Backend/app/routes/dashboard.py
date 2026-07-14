from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.repositories import (
    count_grouped_by_media,
    count_grouped_by_prediction,
)
from app.services.dashboard_service import (
    get_dashboard_summary,
)


router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
)


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
):
    return get_dashboard_summary(db)


@router.get("/by-media-type")
def dashboard_by_media_type(
    db: Session = Depends(get_db),
):
    return {
        "items": count_grouped_by_media(db)
    }


@router.get("/by-result")
def dashboard_by_result(
    db: Session = Depends(get_db),
):
    return {
        "items": count_grouped_by_prediction(db)
    }
