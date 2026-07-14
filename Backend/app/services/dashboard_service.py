from sqlalchemy.orm import Session

from app.database.repositories import (
    average_confidence,
    count_analyses,
    count_grouped_by_media,
    count_grouped_by_prediction,
)


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
        }
    )

    return {
        "total_analyses": count_analyses(db),
        "total_images": by_media.get("image", 0),
        "total_audio": by_media.get("audio", 0),
        "total_videos": by_media.get("video", 0),
        "synthetic_detected": suspicious,
        "authentic_detected": authentic,
        "average_confidence": average_confidence(db),
        "by_media_type": by_media,
        "by_prediction": by_prediction,
    }
