from typing import Any

from app.detector.detector import DetectionResult


SUSPICIOUS_LABELS = {
    "AI",
    "DEEPFAKE",
    "FAKE",
    "SYNTHETIC",
    "MANIPULATED",
    "SPOOF",
}


def _inconclusive_advice(
    media_type: str,
) -> str:
    return {
        "image": (
            "Pruebe con la imagen original, "
            "nítida y sin compresión excesiva."
        ),
        "audio": (
            "Pruebe con una grabación de una sola voz, "
            "de al menos 2.5 segundos, sin música fuerte, "
            "ruido intenso ni saturación."
        ),
        "video": (
            "Pruebe con el video original, con buena "
            "resolución y rostros visibles en varios "
            "fotogramas."
        ),
    }.get(
        media_type,
        "Pruebe con el archivo original "
        "y de buena calidad.",
    )


def build_model_reason(
    result: DetectionResult,
    media_type: str,
    detector_type: str,
) -> str:
    media_name = {
        "image": "la imagen",
        "audio": "el audio",
        "video": "el video",
    }.get(
        media_type,
        "el archivo",
    )

    detector_name = {
        "ai": (
            "generación mediante "
            "inteligencia artificial"
        ),
        "deepfake": (
            "manipulación o deepfake"
        ),
    }.get(
        detector_type,
        "contenido sintético",
    )

    prediction = (
        result.prediction
        .upper()
    )

    if prediction == "INCONCLUSIVE":
        return (
            "El análisis no es concluyente porque "
            "la confianza o el acuerdo interno entre "
            "los segmentos no fue suficiente. "
            f"{_inconclusive_advice(media_type)}"
        )

    if prediction in SUSPICIOUS_LABELS:
        return (
            f"El modelo encontró en {media_name} "
            f"señales compatibles con {detector_name}, "
            f"con una confianza de "
            f"{result.confidence:.2f}%."
        )

    if prediction in {
        "REAL",
        "HUMAN",
        "AUTHENTIC",
        "BONAFIDE",
    }:
        return (
            f"El modelo no encontró en {media_name} "
            f"suficientes señales compatibles con "
            f"{detector_name}. La clasificación REAL "
            f"obtuvo una confianza de "
            f"{result.confidence:.2f}%."
        )

    return (
        f"El modelo devolvió la clase "
        f"{result.prediction} con una confianza "
        f"de {result.confidence:.2f}%."
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
        "prediction": (
            result.prediction
        ),
        "confidence": round(
            float(
                result.confidence
            ),
            2,
        ),
        "probabilities": {
            key: round(
                float(value),
                2,
            )
            for key, value
            in result.probabilities.items()
        },
        "analysis": {
            "model_reason": (
                build_model_reason(
                    result=result,
                    media_type=media_type,
                    detector_type=detector_type,
                )
            ),
            "evidence": (
                result.evidence
            ),
        },
        "model": {
            "name": (
                result.model_name
            ),
            "raw_label": (
                result.raw_label
            ),
        },
        "metadata": (
            result.metadata
        ),
        "processing_time_ms": (
            processing_time_ms
        ),
    }

    if analysis_id is not None:
        payload[
            "analysis_id"
        ] = analysis_id

    if created_at is not None:
        payload[
            "created_at"
        ] = created_at

    return payload