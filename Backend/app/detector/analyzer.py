from typing import Any

from app.detector.detector import DetectionResult


SUSPICIOUS_LABELS = {
    "AI",
    "FAKE",
    "SYNTHETIC",
    "MANIPULATED",
    "SPOOF",
}


def build_model_reason(
    result: DetectionResult,
    media_type: str,
    detector_type: str,
) -> str:
    media_name = {
        "image": "la imagen",
        "audio": "el audio",
        "video": "el video",
    }.get(media_type, "el archivo")

    detector_name = {
        "ai": "generación mediante inteligencia artificial",
        "deepfake": "manipulación o deepfake",
    }.get(detector_type, "contenido sintético")

    if result.prediction.upper() in SUSPICIOUS_LABELS:
        return (
            f"El modelo encontró en {media_name} señales compatibles "
            f"con {detector_name}, con una confianza de "
            f"{result.confidence:.2f}%."
        )

    return (
        f"El modelo no encontró en {media_name} suficientes señales "
        f"compatibles con {detector_name}. La clasificación obtuvo "
        f"una confianza de {result.confidence:.2f}%."
    )


def build_analysis_response(
    *,
    result: DetectionResult,
    media_type: str,
    detector_type: str,
    filename: str,
    processing_time_ms: int,
    analysis_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "media_type": media_type,
        "detector_type": detector_type,
        "filename": filename,
        "prediction": result.prediction,
        "confidence": round(result.confidence, 2),
        "probabilities": {
            key: round(value, 2)
            for key, value in result.probabilities.items()
        },
        "analysis": {
            "model_reason": build_model_reason(
                result,
                media_type,
                detector_type,
            ),
            "evidence": result.evidence,
        },
        "model": {
            "name": result.model_name,
            "raw_label": result.raw_label,
        },
        "metadata": result.metadata,
        "processing_time_ms": processing_time_ms,
    }

    if analysis_id:
        payload["analysis_id"] = analysis_id

    if created_at:
        payload["created_at"] = created_at

    return payload
