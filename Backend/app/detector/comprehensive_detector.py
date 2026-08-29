from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

from app.detector.audio_detector import analyze_audio
from app.detector.detector import DetectionResult
from app.detector.image_ai_detector import analyze_image_ai
from app.detector.image_deepfake_detector import analyze_image_deepfake
from app.detector.video_detector import analyze_video
from app.services.validation_service import get_axis_validation
from app.services.provenance_service import inspect_content_credentials
from app.services.metadata_service import inspect_technical_metadata


SUSPICIOUS_BY_AXIS = {
    "generation": {"AI"},
    "manipulation": {"FAKE", "DEEPFAKE"},
}
AUTHENTIC_BY_AXIS = {
    "generation": {"HUMAN"},
    "manipulation": {"REAL"},
}


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _axis_payload(result: DetectionResult, axis: str) -> dict:
    prediction = result.prediction.upper()
    if prediction == "INCONCLUSIVE":
        status = "inconclusive"
    elif prediction in SUSPICIOUS_BY_AXIS[axis]:
        status = "detected"
    elif prediction in AUTHENTIC_BY_AXIS[axis]:
        status = "not_detected"
    else:
        status = "inconclusive"

    return {
        "status": status,
        "prediction": result.prediction,
        "confidence": round(float(result.confidence), 2),
        "probabilities": {
            key: round(float(value), 2)
            for key, value in result.probabilities.items()
        },
        "model": result.model_name,
        "evidence": result.evidence,
        "metadata": result.metadata,
    }


def _quality_score(media_type: str, generation: DetectionResult,
                   manipulation: DetectionResult) -> tuple[float, list[str]]:
    score = 100.0
    notes: list[str] = []

    if generation.prediction == "INCONCLUSIVE":
        score -= 30
        notes.append("El eje de generación no produjo evidencia suficiente.")
    if manipulation.prediction == "INCONCLUSIVE":
        score -= 30
        notes.append("El eje de manipulación no produjo evidencia suficiente.")

    metadata = manipulation.metadata or {}
    if media_type == "video":
        sampled = int(metadata.get("sampled_frames", 0))
        valid = int(metadata.get("valid_frames", 0))
        if sampled and valid / sampled < 0.5:
            score -= 20
            notes.append("Menos de la mitad de los fotogramas fueron evaluables.")
    elif media_type == "audio":
        if float(metadata.get("clipping_ratio", 0.0)) > 0.05:
            score -= 20
            notes.append("El audio presenta saturación que reduce la fiabilidad.")

    if not notes:
        notes.append("La entrada cumplió las condiciones técnicas del análisis.")
    return max(0.0, score), notes


def _run_pair(path: Path, media_type: str) -> tuple[DetectionResult, DetectionResult]:
    if media_type == "image":
        with Image.open(path) as source:
            image = source.convert("RGB").copy()
        return analyze_image_ai(image), analyze_image_deepfake(image)
    if media_type == "audio":
        return analyze_audio(path, "ai"), analyze_audio(path, "deepfake")
    if media_type == "video":
        return analyze_video(path, "ai"), analyze_video(path, "deepfake")
    raise ValueError(f"Tipo multimedia no soportado: {media_type}")


def _video_audio_analysis(path: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="dfs_audio_") as temp_dir:
        audio_path = Path(temp_dir) / "track.wav"
        command = [
            "ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
            "-vn", "-ac", "1", "-ar", "16000", "-y", str(audio_path),
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=120, check=False
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            return {
                "status": "unavailable",
                "reason": f"No se pudo ejecutar FFmpeg: {type(error).__name__}.",
            }
        if completed.returncode != 0 or not audio_path.exists():
            return {
                "status": "no_audio_track",
                "reason": "El video no contiene una pista de audio evaluable.",
            }
        try:
            generation = analyze_audio(audio_path, "ai")
            manipulation = analyze_audio(audio_path, "deepfake")
        except Exception as error:
            return {
                "status": "inconclusive",
                "reason": f"La pista de audio no fue evaluable: {type(error).__name__}.",
            }
        return {
            "status": "analyzed",
            "generation": _axis_payload(generation, "generation"),
            "manipulation": _axis_payload(manipulation, "manipulation"),
            "fusion_policy": (
                "Las señales visuales y vocales se muestran separadas; "
                "no se fusionan hasta disponer de calibración audiovisual."
            ),
            "lip_sync": "not_assessed",
        }


def analyze_comprehensive(path: str | Path, media_type: str) -> DetectionResult:
    media_path = Path(path)
    generation, manipulation = _run_pair(media_path, media_type)
    axes = {
        "generation": _axis_payload(generation, "generation"),
        "manipulation": _axis_payload(manipulation, "manipulation"),
        "identity_impersonation": {
            "status": "not_assessed",
            "reason": (
                "No se proporcionó una identidad biométrica de referencia. "
                "Detectar un deepfake no demuestra por sí solo suplantación."
            ),
        },
    }
    cross_modal = _video_audio_analysis(media_path) if media_type == "video" else None
    generation_validation = get_axis_validation(media_type, "generation")
    manipulation_validation = get_axis_validation(media_type, "manipulation")
    axes["generation"]["validation_metrics"] = generation_validation
    axes["manipulation"]["validation_metrics"] = manipulation_validation

    detected = [name for name in ("generation", "manipulation")
                if axes[name]["status"] == "detected"]
    inconclusive = [name for name in ("generation", "manipulation")
                    if axes[name]["status"] == "inconclusive"]

    if detected == ["generation"]:
        prediction = "AI"
        confidence = generation.confidence
    elif detected == ["manipulation"]:
        prediction = "DEEPFAKE"
        confidence = manipulation.confidence
    elif len(detected) == 2:
        prediction = "AI_AND_DEEPFAKE"
        confidence = min(generation.confidence, manipulation.confidence)
    elif inconclusive:
        prediction = "INCONCLUSIVE"
        confidence = max(generation.confidence, manipulation.confidence)
    else:
        prediction = "REAL_HUMAN"
        confidence = min(generation.confidence, manipulation.confidence)

    quality_score, quality_notes = _quality_score(
        media_type, generation, manipulation
    )
    provenance = inspect_content_credentials(media_path)
    technical_metadata = inspect_technical_metadata(media_path, media_type)
    evidence = [
        "Los ejes de generación y manipulación se evaluaron por separado.",
        *quality_notes,
        "La confianza es una salida del modelo; no equivale a precisión validada.",
    ]

    return DetectionResult(
        prediction=prediction,
        confidence=float(confidence),
        probabilities={
            "AI": float(generation.probabilities.get("AI", 0.0)),
            "DEEPFAKE": float(
                manipulation.probabilities.get(
                    "DEEPFAKE", manipulation.probabilities.get("FAKE", 0.0)
                )
            ),
        },
        model_name=f"ensemble:{generation.model_name}+{manipulation.model_name}",
        evidence=evidence,
        raw_label=prediction.lower(),
        metadata={
            "schema_version": "3.0",
            "axes": axes,
            "cross_modal": cross_modal,
            "quality": {"score": quality_score, "notes": quality_notes},
            "integrity": {
                "sha256": file_sha256(media_path),
                "provenance": provenance.get("provenance", "unknown"),
                "content_credentials": provenance,
            },
            "technical_metadata": technical_metadata,
            "validation": {
                "calibrated": bool(generation_validation and manipulation_validation),
                "accuracy_claimed": bool(generation_validation and manipulation_validation),
                "message": (
                    "Métricas cargadas desde un conjunto etiquetado."
                    if generation_validation and manipulation_validation
                    else "Requiere evaluación con ground truth independiente."
                ),
                "axes_are_separate": True,
                "identity_requires_reference": True,
            },
        },
    )
