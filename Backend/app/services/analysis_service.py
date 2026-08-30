from pathlib import Path
from hashlib import sha256
from time import perf_counter
from typing import Literal

from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image
from sqlalchemy.orm import Session

from app.database.repositories import create_analysis
from app.detector.analyzer import (
    build_analysis_response,
)
from app.detector.audio_detector import (
    analyze_audio,
)
from app.detector.comprehensive_detector import analyze_comprehensive
from app.detector.image_ai_detector import (
    analyze_image_ai,
)
from app.detector.image_deepfake_detector import (
    analyze_image_deepfake,
)
from app.detector.video_detector import (
    analyze_video,
)
from app.services.file_service import (
    SavedUpload,
    delete_saved_upload,
    save_upload,
)
from app.services.metadata_service import inspect_technical_metadata
from app.services.provenance_service import inspect_content_credentials
from app.services.validation_service import get_axis_validation


MediaType = Literal[
    "image",
    "audio",
    "video",
]

DetectorType = Literal[
    "ai",
    "deepfake",
    "comprehensive",
]


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _enrich_individual_result(
    *,
    result,
    path: Path,
    media_type: MediaType,
    detector_type: DetectorType,
) -> None:
    """Añade trazabilidad y aplica declaraciones de procedencia verificables."""
    axis = "generation" if detector_type == "ai" else "manipulation"
    validation = get_axis_validation(media_type, axis)
    technical = inspect_technical_metadata(path, media_type)
    credentials = inspect_content_credentials(path)
    declarations = credentials.get("declarations", {})
    provenance_prediction = None
    provenance_labels = None
    if declarations.get("ai_provenance_declared"):
        if detector_type == "ai" and media_type in {"image", "video"}:
            provenance_prediction = "AI"
            provenance_labels = ("AI", "HUMAN")
        elif detector_type == "deepfake" and media_type == "image":
            provenance_prediction = "FAKE"
            provenance_labels = ("FAKE", "REAL")

    if provenance_prediction and provenance_labels:
        suspicious_label, authentic_label = provenance_labels
        result.metadata["visual_model_prediction"] = result.prediction
        result.metadata["visual_model_confidence"] = result.confidence
        result.metadata["visual_model_probabilities"] = dict(
            result.probabilities
        )
        result.metadata["decision_basis"] = "content_credentials"
        result.metadata["confidence_type"] = "verified_provenance_declaration"
        result.prediction = provenance_prediction
        result.confidence = 100.0
        result.probabilities = {
            suspicious_label: 100.0,
            authentic_label: 0.0,
        }
        result.raw_label = "c2pa_trained_algorithmic_media"
        visual_suspicious = result.metadata["visual_model_probabilities"].get(
            suspicious_label, 0.0
        )
        visual_authentic = result.metadata["visual_model_probabilities"].get(
            authentic_label, 0.0
        )
        result.evidence = [
            "Las Content Credentials declaran que el contenido fue creado "
            "o editado mediante IA (trainedAlgorithmicMedia).",
            "La cadena C2PA registra acciones de Google Generative AI y una "
            "marca de agua SynthID.",
            "La salida del clasificador visual se conserva por separado: "
            f"{suspicious_label} {visual_suspicious:.2f}% frente a "
            f"{authentic_label} {visual_authentic:.2f}%.",
            "El veredicto se basa en procedencia declarada y no confirma la "
            "identidad de la persona representada.",
        ]
    technologies = [
        {
            "technology": "SHA-256",
            "status": "executed",
            "purpose": "Fijar la identidad binaria del archivo analizado.",
            "observation": "Hash calculado sobre el archivo recibido.",
        },
        {
            "technology": "C2PA / Content Credentials",
            "status": (
                "executed"
                if credentials.get("status") != "sdk_unavailable"
                else "unavailable"
            ),
            "purpose": "Examinar procedencia e integridad declaradas.",
            "observation": credentials.get("message", "Sin observación."),
        },
        {
            "technology": "Metadatos técnicos",
            "status": "executed" if technical.get("status") != "unreadable" else "inconclusive",
            "purpose": "Caracterizar formato, dimensiones, duración, códecs y etiquetas.",
            "observation": (
                f"Formato: {technical.get('format') or technical.get('format_name') or 'desconocido'}."
            ),
        },
    ]
    if media_type == "image":
        forensic = technical.get("forensic_metadata", {})
        stats = forensic.get("statistics", {})
        binary = forensic.get("binary", {})
        consistency = forensic.get("consistency", {})
        technologies.extend([
            {
                "technology": "EXIF / IPTC / XMP",
                "status": "executed",
                "purpose": "Examinar captura, software, autoría y declaraciones editoriales.",
                "observation": f"EXIF: {stats.get('exif_fields', 0)} campos; IPTC: {stats.get('iptc_fields', 0)}; XMP: {'presente' if stats.get('xmp_present') else 'ausente'}.",
            },
            {
                "technology": "Estructura binaria JPEG",
                "status": "executed" if technical.get("format") == "JPEG" else "not_applicable",
                "purpose": "Extraer tablas DQT, marcadores APP, comentarios y señales de miniatura.",
                "observation": f"DQT: {stats.get('dqt_tables', 0)}; APP: {stats.get('app_segments', 0)}; COM: {stats.get('binary_comments', 0)}; APP1 duplicado: {binary.get('duplicate_app1', False)}.",
            },
            {
                "technology": "Cruce de consistencia forense",
                "status": "executed",
                "purpose": "Contrastar formato, extensión, relación de aspecto y tiempos declarados.",
                "observation": f"Extensión coherente: {consistency.get('extension_consistent')}; ratio cercano: {consistency.get('nearest_standard_ratio', 'N/D')}; estado temporal: {consistency.get('temporal_status', 'N/D')}.",
            },
        ])
    if media_type == "video":
        technologies.extend([
            {
                "technology": "Muestreo temporal",
                "status": "executed",
                "purpose": "Cubrir distintos instantes del video.",
                "observation": f"{result.metadata.get('sampled_frames', 0)} fotogramas muestreados; {result.metadata.get('valid_frames', 0)} evaluables.",
            },
            {
                "technology": "Agregación temporal",
                "status": "executed",
                "purpose": "Combinar mediana y acuerdo entre fotogramas.",
                "observation": f"Mediana de sospecha: {result.metadata.get('median_suspicious_score', 'N/D')}%.",
            },
        ])
    if media_type == "audio":
        technologies.append({
            "technology": "Segmentación acústica",
            "status": "executed",
            "purpose": "Contrastar varios tramos de la señal.",
            "observation": f"{result.metadata.get('chunk_count', 0)} segmentos analizados.",
        })
    if detector_type == "deepfake" and media_type in {"image", "video"}:
        technologies.append({
            "technology": "Detección facial OpenCV",
            "status": "executed",
            "purpose": "Verificar que existan regiones faciales evaluables.",
            "observation": f"{result.metadata.get('faces_detected', result.metadata.get('valid_frames', 0))} candidatos/frames faciales detectados.",
        })
    visual_prediction = result.metadata.get(
        "visual_model_prediction", result.prediction
    )
    visual_confidence = result.metadata.get(
        "visual_model_confidence", result.confidence
    )
    technologies.insert(0, {
        "technology": "Clasificador de IA",
        "status": (
            "not_executed"
            if detector_type == "deepfake" and media_type == "image"
            and not result.metadata.get("quality_ok", True)
            else "executed"
        ),
        "purpose": "Estimar la clase solicitada mediante el checkpoint registrado.",
        "observation": f"Modelo: {result.model_name}; resultado: {visual_prediction}; score: {visual_confidence:.2f}%.",
    })

    result.metadata.update(
        {
            "technology_evidence": technologies,
            "technical_metadata": technical,
            "integrity": {
                "sha256": _file_sha256(path),
                "content_credentials": credentials,
            },
            "validation": {
                "axis": axis,
                "calibrated": bool(validation),
                "metrics": validation,
                "message": (
                    "Métricas cargadas desde un conjunto etiquetado."
                    if validation
                    else "Requiere evaluación con ground truth independiente."
                ),
            },
        }
    )


def normalize_detector_type(
    detector_type: str,
) -> DetectorType:
    value = (
        detector_type
        .strip()
        .lower()
    )

    aliases = {
        "ai": "ai",
        "ia": "ai",
        "generated": "ai",
        "synthetic": "ai",
        "deepfake": "deepfake",
        "fake": "deepfake",
        "comprehensive": "comprehensive",
        "complete": "comprehensive",
        "completo": "comprehensive",
    }

    normalized = aliases.get(
        value
    )

    if normalized is None:
        raise ValueError(
            "detector_type debe ser "
            "'ai', 'deepfake' o 'comprehensive'."
        )

    return normalized  # type: ignore[return-value]


def _run_image_detector(
    path: Path,
    detector_type: DetectorType,
):
    with Image.open(path) as image:
        image_copy = (
            image.convert("RGB").copy()
        )

    if detector_type == "ai":
        return analyze_image_ai(
            image_copy
        )

    return analyze_image_deepfake(
        image_copy
    )


def _run_audio_detector(
    path: Path,
    detector_type: DetectorType,
):
    return analyze_audio(
        path,
        detector_type=detector_type,
    )


def _run_video_detector(
    path: Path,
    detector_type: DetectorType,
):
    return analyze_video(
        path,
        detector_type=detector_type,
    )


async def analyze_upload(
    *,
    upload: UploadFile,
    media_type: MediaType,
    detector_type: str,
    db: Session,
) -> dict:
    normalized_detector = (
        normalize_detector_type(
            detector_type
        )
    )

    saved: SavedUpload | None = None
    started_at = perf_counter()

    try:
        saved = await save_upload(
            upload,
            media_type,
        )

        if normalized_detector == "comprehensive":
            result = await run_in_threadpool(
                analyze_comprehensive,
                saved.path,
                media_type,
            )

        elif media_type == "image":
            result = await run_in_threadpool(
                _run_image_detector,
                saved.path,
                normalized_detector,
            )

        elif media_type == "audio":
            result = await run_in_threadpool(
                _run_audio_detector,
                saved.path,
                normalized_detector,
            )

        elif media_type == "video":
            result = await run_in_threadpool(
                _run_video_detector,
                saved.path,
                normalized_detector,
            )

        else:
            raise ValueError(
                "Tipo multimedia no soportado: "
                f"{media_type}"
            )

        if normalized_detector != "comprehensive":
            _enrich_individual_result(
                result=result,
                path=saved.path,
                media_type=media_type,
                detector_type=normalized_detector,
            )

        processing_time_ms = round(
            (
                perf_counter()
                - started_at
            )
            * 1000
        )

        record = create_analysis(
            db,
            original_filename=(
                saved.original_filename
            ),
            stored_filename=(
                saved.stored_filename
            ),
            file_path=str(
                saved.path
            ),
            content_type=(
                saved.content_type
            ),
            size_bytes=(
                saved.size_bytes
            ),
            media_type=media_type,
            detector_type=(
                normalized_detector
            ),
            prediction=(
                result.prediction
            ),
            confidence=(
                result.confidence
            ),
            probabilities=(
                result.probabilities
            ),
            evidence=(
                result.evidence
            ),
            model_name=(
                result.model_name
            ),
            analysis_metadata=(
                result.metadata
            ),
            processing_time_ms=(
                processing_time_ms
            ),
            status="completed",
            error_message=None,
        )

        return build_analysis_response(
            result=result,
            media_type=media_type,
            detector_type=(
                normalized_detector
            ),
            filename=(
                saved.original_filename
            ),
            processing_time_ms=(
                processing_time_ms
            ),
            analysis_id=record.id,
            created_at=(
                record.created_at
                .isoformat()
            ),
        )

    except Exception:
        delete_saved_upload(
            saved
        )
        raise
