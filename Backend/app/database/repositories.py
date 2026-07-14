from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.database.models import Analysis


def create_analysis(db: Session, **data: Any) -> Analysis:
    record = Analysis(**data)

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


def get_analysis(
    db: Session,
    analysis_id: str,
) -> Analysis | None:
    return db.get(Analysis, analysis_id)


def list_analyses(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    media_type: str | None = None,
    detector_type: str | None = None,
    prediction: str | None = None,
) -> list[Analysis]:
    statement = select(Analysis)

    if media_type:
        statement = statement.where(
            Analysis.media_type == media_type
        )

    if detector_type:
        statement = statement.where(
            Analysis.detector_type == detector_type
        )

    if prediction:
        statement = statement.where(
            Analysis.prediction == prediction
        )

    statement = (
        statement
        .order_by(desc(Analysis.created_at))
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def count_analyses(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(Analysis.id))
        )
        or 0
    )


def average_confidence(db: Session) -> float:
    return round(
        float(
            db.scalar(
                select(func.avg(Analysis.confidence))
            )
            or 0.0
        ),
        2,
    )


def count_grouped_by_media(
    db: Session,
) -> dict[str, int]:
    rows = db.execute(
        select(
            Analysis.media_type,
            func.count(Analysis.id),
        ).group_by(Analysis.media_type)
    ).all()

    return {
        str(media_type): int(total)
        for media_type, total in rows
    }


def count_grouped_by_prediction(
    db: Session,
) -> dict[str, int]:
    rows = db.execute(
        select(
            Analysis.prediction,
            func.count(Analysis.id),
        ).group_by(Analysis.prediction)
    ).all()

    return {
        str(prediction): int(total)
        for prediction, total in rows
    }


def update_report_path(
    db: Session,
    record: Analysis,
    report_path: str,
) -> Analysis:
    record.report_path = report_path
    db.add(record)
    db.commit()
    db.refresh(record)

    return record


def analysis_to_dict(
    record: Analysis,
    *,
    include_file_path: bool = False,
) -> dict[str, Any]:
    suspicious = record.prediction.upper() in {
        "AI",
        "FAKE",
        "SYNTHETIC",
        "MANIPULATED",
        "SPOOF",
    }

    reason = (
        "El modelo encontró señales compatibles con contenido "
        "sintético o manipulado."
        if suspicious
        else
        "El modelo no encontró suficientes señales para clasificar "
        "el contenido como sintético o manipulado."
    )

    payload: dict[str, Any] = {
        "analysis_id": record.id,
        "created_at": record.created_at.isoformat(),
        "filename": record.original_filename,
        "media_type": record.media_type,
        "detector_type": record.detector_type,
        "prediction": record.prediction,
        "confidence": round(record.confidence, 2),
        "probabilities": record.probabilities,
        "analysis": {
            "model_reason": reason,
            "evidence": record.evidence,
        },
        "model": {
            "name": record.model_name,
        },
        "processing_time_ms": record.processing_time_ms,
        "status": record.status,
        "report_available": bool(record.report_path),
    }

    if include_file_path:
        payload.update(
            {
                "file_path": record.file_path,
                "stored_filename": record.stored_filename,
                "content_type": record.content_type,
                "size_bytes": record.size_bytes,
                "report_path": record.report_path,
            }
        )

    return payload
