from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.repositories import (
    get_analysis,
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

    report_bytes = create_pdf_report(record)
    return StreamingResponse(
        BytesIO(report_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="DeepFakeShield_{analysis_id}.pdf"'
            ),
            "Cache-Control": "no-store",
        },
    )
