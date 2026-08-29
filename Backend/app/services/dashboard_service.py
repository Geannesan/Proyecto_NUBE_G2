from sqlalchemy.orm import Session

from app.database.repositories import (
    average_confidence,
    count_analyses,
    count_grouped_by_media,
    count_grouped_by_prediction,
)
from app.services.validation_service import load_validation_report


def get_dashboard_summary(
    db: Session,
) -> dict:
    by_media = count_grouped_by_media(db)
    by_prediction = count_grouped_by_prediction(db)

    suspicious = sum(
        total
        for prediction, total in by_prediction.items()
        if prediction.upper()
        in {
            "AI",
            "FAKE",
            "SYNTHETIC",
            "MANIPULATED",
            "SPOOF",
            "DEEPFAKE",
            "AI_AND_DEEPFAKE",
        }
    )

    authentic = sum(
        total
        for prediction, total in by_prediction.items()
        if prediction.upper()
        in {
            "HUMAN",
            "REAL",
            "AUTHENTIC",
            "BONAFIDE",
            "REAL_HUMAN",
        }
    )

    inconclusive = by_prediction.get("INCONCLUSIVE", 0)
    validation_report = load_validation_report()

    return {
        "total_analyses": count_analyses(db),
        "total_images": by_media.get("image", 0),
        "total_audio": by_media.get("audio", 0),
        "total_videos": by_media.get("video", 0),
        "synthetic_detected": suspicious,
        "authentic_detected": authentic,
        "average_confidence": average_confidence(db),
        "average_model_confidence": average_confidence(db),
        "inconclusive": inconclusive,
        "validation": {
            "ground_truth_available": validation_report is not None,
            "metrics_by_media_and_axis": (
                validation_report.get("groups", {}) if validation_report else {}
            ),
            "message": (
                "Métricas calculadas con el dataset etiquetado configurado."
                if validation_report
                else "La confianza media no representa accuracy. Ejecute la evaluación offline con datos etiquetados."
            ),
        },
        "by_media_type": by_media,
        "by_prediction": by_prediction,
    }
