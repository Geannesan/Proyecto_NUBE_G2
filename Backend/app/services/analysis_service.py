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
from app.services.reference_comparison_service import compare_with_original
from app.services.training_data_service import find_reviewed_sample, register_ai_edited_pair
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


def _operational_evidence_quality(result, technical: dict, media_type: str) -> dict:
    """Índice técnico reproducible; no representa accuracy ni calibración."""
    confidence = max(0.0, min(100.0, float(result.confidence or 0.0)))
    separation = max(0.0, min(100.0, abs(confidence - 50.0) * 2.0))
    trace_coverage = 0.0
    if media_type == "image":
        width = int(technical.get("width") or 0)
        height = int(technical.get("height") or 0)
        input_quality = min(100.0, min(width, height) / 512.0 * 100.0)
        trace_coverage = float(
            technical.get("forensic_metadata", {})
            .get("statistics", {})
            .get("metadata_coverage_percent", 0.0)
        )
    elif media_type == "video":
        sampled = int(result.metadata.get("sampled_frames", 0))
        valid = int(result.metadata.get("valid_frames", 0))
        input_quality = (valid / sampled * 100.0) if sampled else 60.0
        trace_coverage = 100.0 if technical.get("status") == "available" else 0.0
    else:
        clipping = max(0.0, min(1.0, float(result.metadata.get("clipping_ratio", 0.0))))
        input_quality = (1.0 - clipping) * 100.0
        trace_coverage = 100.0 if technical.get("status") == "available" else 0.0
    score = 0.45 * input_quality + 0.35 * separation + 0.20 * trace_coverage
    return {
        "score": round(max(0.0, min(100.0, score)), 2),
        "method": "0.45 calidad de entrada + 0.35 separación del score + 0.20 cobertura técnica",
        "components": {
            "input_quality_percent": round(input_quality, 2),
            "model_separation_percent": round(separation, 2),
            "technical_coverage_percent": round(trace_coverage, 2),
        },
        "interpretation": "Índice operativo de suficiencia de evidencia; no equivale a accuracy.",
    }


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
    if media_type == "image":
        for key in ("faces_detected", "face_detection_status", "largest_face_area_percent", "face_detector"):
            if key in technical:
                result.metadata.setdefault(key, technical[key])
    result.metadata.setdefault(
        "quality", _operational_evidence_quality(result, technical, media_type)
    )
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
    if media_type == "image":
        technologies.append({
            "technology": "Detección facial OpenCV",
            "status": "executed",
            "purpose": "Contar regiones faciales candidatas independientemente del veredicto.",
            "observation": f"{result.metadata.get('faces_detected', 0)} candidatos faciales; mayor rostro: {result.metadata.get('largest_face_area_percent', 0)}% del área.",
        })
    elif media_type == "video":
        technologies.append({
            "technology": "Detección facial OpenCV", "status": "executed",
            "purpose": "Contar regiones faciales candidatas en los fotogramas muestreados.",
            "observation": (
                f"{result.metadata.get('face_detections_total', 0)} detecciones faciales "
                f"en {result.metadata.get('frames_with_faces', 0)} fotogramas; "
                f"máximo {result.metadata.get('max_faces_in_frame', 0)} en un fotograma."
            ),
        })
    comparison = result.metadata.get("reference_comparison")
    if comparison:
        technologies.append({
            "technology": "Comparación con original",
            "status": "executed",
            "purpose": "Alinear la escena y medir cambios visuales respecto de una referencia aportada.",
            "observation": (
                f"Estado: {comparison.get('status')}; "
                f"área cambiada: {comparison.get('changed_area_over_25_percent', 0)}%; "
                f"coincidencias: {comparison.get('feature_matches', 0)}; "
                f"SHA-256 referencia: {comparison.get('reference_sha256', 'N/D')}."
            ),
        })
    reviewed_sample = result.metadata.get("reviewed_sample")
    if reviewed_sample:
        technologies.append({
            "technology": "Registro supervisado de pares",
            "status": "executed",
            "purpose": "Reconocer archivos exactos cuya etiqueta y original ya fueron revisados.",
            "observation": (
                f"Coincidencia SHA-256 exacta; rol {reviewed_sample.get('sample_role')}; "
                f"etiqueta del par {reviewed_sample.get('label')}; "
                f"par {reviewed_sample.get('pair_id')}. No es probabilidad del modelo."
            ),
        })
    ai_edited_candidate = result.metadata.get("ai_edited_candidate")
    if ai_edited_candidate:
        candidate_probabilities = ai_edited_candidate.get("probabilities", {})
        technologies.append({
            "technology": "Candidato AI_EDITED",
            "status": "executed_shadow",
            "purpose": "Distinguir ediciones localizadas con IA de fotografías reales.",
            "observation": (
                f"AI_EDITED: {candidate_probabilities.get('AI_EDITED', 0):.2f}%; "
                f"REAL: {candidate_probabilities.get('REAL', 0):.2f}%; "
                f"validación interna: {ai_edited_candidate.get('validation_accuracy', 0):.2f}%; "
                f"pares: {ai_edited_candidate.get('training_pairs', 0) + ai_edited_candidate.get('validation_pairs', 0)}/"
                f"{ai_edited_candidate.get('minimum_promotion_pairs', 30)}. No contribuye aún al veredicto."
            ),
        })
    visual_prediction = result.metadata.get(
        "visual_model_prediction", result.prediction
    )
    visual_confidence = result.metadata.get(
        "visual_model_confidence", result.confidence
    )
    technologies.insert(0, {
        "technology": (
            "Clasificador deepfake"
            if detector_type == "deepfake"
            else "Clasificador de IA"
        ),
        "status": (
            "not_executed"
            if detector_type == "deepfake" and media_type == "image"
            and not result.metadata.get("face_results")
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
    reference_upload: UploadFile | None = None,
    contribute_training: bool = False,
) -> dict:
    normalized_detector = (
        normalize_detector_type(
            detector_type
        )
    )

    saved: SavedUpload | None = None
    reference_saved: SavedUpload | None = None
    started_at = perf_counter()

    try:
        saved = await save_upload(
            upload,
            media_type,
        )
        if reference_upload is not None:
            if media_type != "image":
                raise ValueError("La referencia original solo está disponible para imágenes.")
            reference_saved = await save_upload(reference_upload, "image")

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

        reviewed_sample = await run_in_threadpool(find_reviewed_sample, saved.path)
        if reviewed_sample is not None and normalized_detector in {"ai", "deepfake"}:
            suspicious = "AI" if normalized_detector == "ai" else "FAKE"
            authentic = "HUMAN" if normalized_detector == "ai" else "REAL"
            is_original = reviewed_sample.get("sample_role") == "original"
            prediction = authentic if is_original else suspicious
            alternative = suspicious if is_original else authentic
            result.prediction = prediction
            result.confidence = 100.0
            result.probabilities = {prediction: 100.0, alternative: 0.0}
            result.raw_label = (
                "reviewed_original_sample" if is_original
                else "reviewed_edited_sample"
            )
            result.model_name = f"{result.model_name}+reviewed-sample-registry"
            result.metadata["reviewed_sample"] = reviewed_sample
            result.evidence = [
                f"Coincidencia SHA-256 exacta con una muestra {reviewed_sample['sample_role']} revisada.",
                "La etiqueta procede del corpus supervisado y no de una nueva inferencia del clasificador.",
                f"Par revisado: {reviewed_sample['pair_id']}.",
                *result.evidence,
            ]

        if reference_saved is not None:
            comparison = await run_in_threadpool(
                compare_with_original, saved.path, reference_saved.path
            )
            comparison["reference_filename"] = reference_saved.original_filename
            result.metadata["reference_comparison"] = comparison
            if comparison["changes_confirmed"]:
                suspicious = "AI" if normalized_detector == "ai" else "FAKE"
                authentic = "HUMAN" if normalized_detector == "ai" else "REAL"
                score = float(comparison["confidence"])
                result.prediction = suspicious
                result.confidence = score
                result.probabilities = {suspicious: score, authentic: 100.0 - score}
                result.raw_label = "reference_assisted_visual_manipulation"
                result.model_name = f"{result.model_name}+reference-change-detector"
                result.evidence = [
                    f"La imagen fue alineada con la referencia original mediante {comparison['feature_matches']} coincidencias visuales.",
                    f"Se confirmó cambio sustancial en {comparison['changed_area_over_25_percent']}% del área comparable.",
                    "El cotejo incluye cambios de escena, texto, vestuario y regiones faciales.",
                    comparison["caveat"],
                    *result.evidence,
                ]
                if contribute_training:
                    result.metadata["training_contribution"] = await run_in_threadpool(
                        register_ai_edited_pair,
                        edited=saved,
                        original=reference_saved,
                        comparison=comparison,
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
        delete_saved_upload(reference_saved)
        raise
