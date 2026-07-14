from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.repositories import (
    get_analysis,
    update_report_path,
)
from app.services.report_service import (
    create_pdf_report,
)


router = APIRouter(
    prefix="/api/v1/reports",
    tags=["Reports"],
)


@router.get("/{analysis_id}")
def download_report(
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

    report_path = (
        Path(record.report_path)
        if record.report_path
        else None
    )

    if (
        report_path is None
        or not report_path.exists()
    ):
        report_path = create_pdf_report(record)

        update_report_path(
            db,
            record,
            str(report_path),
        )

    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        filename=(
            f"DeepFakeShield_{analysis_id}.pdf"
        ),
    )
