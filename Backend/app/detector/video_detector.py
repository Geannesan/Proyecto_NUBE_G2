import os
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

from app.detector.detector import DetectionResult
from app.detector.image_ai_detector import normalize_ai_label
from app.detector.image_deepfake_detector import normalize_deepfake_label
from app.detector.model_loader import (
    VIDEO_AI_MODEL_NAME,
    VIDEO_AI_SECONDARY_MODEL_NAME,
    VIDEO_DEEPFAKE_MODEL_NAME,
    load_video_ai_components,
    load_video_ai_secondary_components,
    load_video_deepfake_components,
)


MAX_VIDEO_FRAMES = int(os.getenv("MAX_VIDEO_FRAMES", "32"))
VIDEO_THRESHOLD = float(os.getenv("VIDEO_THRESHOLD", "60"))
VIDEO_HUMAN_THRESHOLD = float(os.getenv("VIDEO_HUMAN_THRESHOLD", "70"))
MIN_VALID_VIDEO_FRAMES = int(os.getenv("MIN_VALID_VIDEO_FRAMES", "3"))
MIN_SUSPICIOUS_VIDEO_FRAMES = int(
    os.getenv("MIN_SUSPICIOUS_VIDEO_FRAMES", "2")
)
MIN_SUSPICIOUS_VIDEO_RATIO = float(
    os.getenv("MIN_SUSPICIOUS_VIDEO_RATIO", "0.10")
)


def _model_label(model, index: int) -> str:
    labels = getattr(model.config, "id2label", {}) or {}
    return str(labels.get(index, labels.get(str(index), f"LABEL_{index}")))


def _classify_frame(image: Image.Image, detector_type: str) -> DetectionResult:
    """Clasifica un fotograma con los modelos dedicados exclusivamente a video."""
    if detector_type == "ai":
        processor, model, device = load_video_ai_components()
        normalize = normalize_ai_label
        suspicious_label, normal_label = "AI", "HUMAN"
        model_name = VIDEO_AI_MODEL_NAME
    else:
        processor, model, device = load_video_deepfake_components()
        normalize = normalize_deepfake_label
        suspicious_label, normal_label = "FAKE", "REAL"
        model_name = VIDEO_DEEPFAKE_MODEL_NAME

        # El checkpoint deepfake es facial: se analiza el rostro dominante con
        # contexto alrededor, tal como fue diseñado el detector de referencia.
        rgb_array = np.asarray(image.convert("RGB"))
        gray = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2GRAY)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(64, 64)
        )
        if len(faces) == 0:
            return DetectionResult(
                prediction="INCONCLUSIVE",
                confidence=0.0,
                probabilities={"FAKE": 0.0, "REAL": 0.0},
                model_name=model_name,
                evidence=["No se detectó un rostro frontal en el fotograma."],
                raw_label="inconclusive",
            )
        x, y, width, height = max(faces, key=lambda face: int(face[2]) * int(face[3]))
        margin = int(max(width, height) * 0.25)
        image = image.crop((
            max(0, int(x) - margin),
            max(0, int(y) - margin),
            min(image.width, int(x + width) + margin),
            min(image.height, int(y + height) + margin),
        ))

    def infer(current_processor, current_model, current_device):
        inputs = current_processor(images=image.convert("RGB"), return_tensors="pt")
        inputs = {key: value.to(current_device) for key, value in inputs.items()}
        with torch.inference_mode():
            logits = current_model(**inputs).logits

        if logits.shape[-1] == 1:
            suspicious = float(torch.sigmoid(logits)[0, 0].item() * 100)
            return {
                suspicious_label: suspicious,
                normal_label: 100.0 - suspicious,
            }, ("generated" if detector_type == "ai" else "fake")

        values = torch.softmax(logits, dim=-1)[0]
        current_probabilities = {suspicious_label: 0.0, normal_label: 0.0}
        for index, value in enumerate(values):
            normalized = normalize(_model_label(current_model, index))
            if normalized in current_probabilities:
                current_probabilities[normalized] += float(value.item() * 100)
        return current_probabilities, _model_label(
            current_model, int(values.argmax().item())
        )

    probabilities, raw_label = infer(processor, model, device)
    model_probabilities = {
        VIDEO_AI_MODEL_NAME if detector_type == "ai" else model_name: dict(probabilities)
    }

    if detector_type == "ai":
        secondary_processor, secondary_model, secondary_device = (
            load_video_ai_secondary_components()
        )
        secondary_probabilities, secondary_raw_label = infer(
            secondary_processor, secondary_model, secondary_device
        )
        model_probabilities[VIDEO_AI_SECONDARY_MODEL_NAME] = dict(
            secondary_probabilities
        )
        probabilities = {
            key: (probabilities[key] + secondary_probabilities[key]) / 2.0
            for key in (suspicious_label, normal_label)
        }
        raw_label = f"{raw_label}+{secondary_raw_label}"
        model_name = (
            f"ensemble:{VIDEO_AI_MODEL_NAME}+{VIDEO_AI_SECONDARY_MODEL_NAME}"
        )

    # Una configuración sin nombres de clase fiables no debe producir un
    # veredicto silencioso con probabilidades en cero.
    if sum(probabilities.values()) < 99.0:
        return DetectionResult(
            prediction="INCONCLUSIVE",
            confidence=0.0,
            probabilities={suspicious_label: 0.0, normal_label: 0.0},
            model_name=model_name,
            evidence=[f"Etiquetas del modelo no reconocidas: {model.config.id2label}"],
            raw_label=raw_label,
        )

    prediction = max(probabilities, key=probabilities.get)
    return DetectionResult(
        prediction=prediction,
        confidence=probabilities[prediction],
        probabilities=probabilities,
        model_name=model_name,
        evidence=[f"Fotograma clasificado por {model_name}."],
        raw_label=raw_label,
        metadata={"model_probabilities": model_probabilities},
    )


def _suspicious_probability(result: DetectionResult, detector_type: str) -> float:
    suspicious_key = "AI" if detector_type == "ai" else "FAKE"
    if suspicious_key in result.probabilities:
        return float(result.probabilities[suspicious_key])
    if result.prediction == suspicious_key:
        return float(result.confidence)
    return max(0.0, 100.0 - float(result.confidence))


def _is_valid_result(result: DetectionResult, detector_type: str) -> bool:
    """Do not turn an unassessable frame into suspicious evidence."""
    if result.prediction == "INCONCLUSIVE":
        return False
    expected = {"AI", "HUMAN"} if detector_type == "ai" else {"FAKE", "REAL"}
    return result.prediction in expected


def _sample_frame_indexes(total_frames: int, sample_count: int) -> np.ndarray:
    """Sample bin centres and avoid black intro/outro boundary frames."""
    bin_width = total_frames / sample_count
    indexes = [
        min(total_frames - 1, int((index + 0.5) * bin_width))
        for index in range(sample_count)
    ]
    return np.asarray(sorted(set(indexes)), dtype=int)


def _required_suspicious_frames(valid_frame_count: int) -> int:
    return max(
        MIN_SUSPICIOUS_VIDEO_FRAMES,
        int(np.ceil(valid_frame_count * MIN_SUSPICIOUS_VIDEO_RATIO)),
    )


def analyze_video(video_path: str | Path, detector_type: str = "deepfake") -> DetectionResult:
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el video: {path}")

    detector_type = detector_type.strip().lower()
    if detector_type not in {"ai", "deepfake"}:
        raise ValueError("detector_type debe ser 'ai' o 'deepfake'.")

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("OpenCV no pudo abrir el video.")

    try:
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        if total_frames <= 0:
            raise ValueError("No se pudieron determinar los fotogramas.")

        frame_indexes = _sample_frame_indexes(total_frames, min(MAX_VIDEO_FRAMES, total_frames))
        frame_results: list[tuple[int, DetectionResult]] = []
        for frame_index in frame_indexes:
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
            success, frame = capture.read()
            if not success or frame is None:
                continue
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            result = _classify_frame(image, detector_type)
            frame_results.append((int(frame_index), result))
    finally:
        capture.release()

    if not frame_results:
        raise ValueError("No se extrajeron fotogramas válidos.")

    suspicious_label = "AI" if detector_type == "ai" else "FAKE"
    normal_label = "HUMAN" if detector_type == "ai" else "REAL"
    valid_results = [item for item in frame_results if _is_valid_result(item[1], detector_type)]
    discarded_frames = len(frame_results) - len(valid_results)
    duration_seconds = total_frames / fps if fps > 0 else 0.0

    if not valid_results:
        return DetectionResult(
            prediction="INCONCLUSIVE",
            confidence=0.0,
            probabilities={suspicious_label: 0.0, normal_label: 0.0},
            model_name=f"temporal-frame-aggregation:{frame_results[0][1].model_name}",
            evidence=[
                "Ningún fotograma contenía evidencia visual suficiente.",
                "Para deepfake, el video debe mostrar al menos un rostro frontal y visible.",
            ],
            raw_label="inconclusive",
            metadata={
                "total_frames": total_frames,
                "sampled_frames": len(frame_results),
                "valid_frames": 0,
                "discarded_frames": discarded_frames,
                "fps": round(fps, 2),
                "duration_seconds": round(duration_seconds, 2),
            },
        )

    scores = [_suspicious_probability(result, detector_type) for _, result in valid_results]
    frame_scores = [
        {
            "frame": frame_index,
            "time_seconds": round(frame_index / fps, 3) if fps > 0 else None,
            "suspicious_score": round(
                _suspicious_probability(result, detector_type), 2
            ),
            "prediction": result.prediction,
            "confidence": round(float(result.confidence), 2),
        }
        for frame_index, result in valid_results
    ]
    mean_score = float(np.mean(scores))
    median_score = float(np.median(scores))
    maximum_score = float(np.max(scores))
    vote_ratio = float(np.mean(np.asarray(scores) >= VIDEO_THRESHOLD))
    suspicious_scores = [score for score in scores if score >= VIDEO_THRESHOLD]
    required_suspicious_frames = _required_suspicious_frames(len(scores))
    per_model_medians: dict[str, float] = {}
    model_disagreement = 0.0
    if detector_type == "ai":
        for configured_model in (VIDEO_AI_MODEL_NAME, VIDEO_AI_SECONDARY_MODEL_NAME):
            model_scores = [
                float(item.metadata.get("model_probabilities", {})
                      .get(configured_model, {}).get("AI", 0.0))
                for _, item in valid_results
            ]
            per_model_medians[configured_model] = float(np.median(model_scores))
        model_disagreement = abs(
            per_model_medians[VIDEO_AI_MODEL_NAME]
            - per_model_medians[VIDEO_AI_SECONDARY_MODEL_NAME]
        )

    # Detectar un tramo manipulado basta para marcar el video completo. Usar la
    # mediana global ocultaba deepfakes parciales detrás de intros y cierres
    # auténticos. Se exigen varias muestras fuertes para ignorar picos aislados.
    if len(suspicious_scores) >= required_suspicious_frames:
        prediction = suspicious_label
        confidence = float(np.mean(suspicious_scores))
    elif (100.0 - median_score) >= VIDEO_HUMAN_THRESHOLD:
        prediction, confidence = normal_label, 100.0 - median_score
    else:
        prediction, confidence = "INCONCLUSIVE", max(
            median_score, 100.0 - median_score
        )

    suspicious_position = int(np.argmax(scores))
    suspicious_frame = valid_results[suspicious_position][0]
    base_model_name = valid_results[0][1].model_name
    reported_suspicious_score = (
        confidence if prediction == suspicious_label else median_score
    )

    return DetectionResult(
        prediction=prediction,
        confidence=confidence,
        probabilities={
            suspicious_label: reported_suspicious_score,
            normal_label: 100.0 - reported_suspicious_score,
        },
        model_name=f"temporal-frame-aggregation:{base_model_name}",
        evidence=[
            f"Se usaron {len(valid_results)} de {len(frame_results)} fotogramas muestreados.",
            f"Mediana de sospecha: {median_score:.2f}%.",
            f"Promedio de sospecha: {mean_score:.2f}%.",
            f"Máxima sospecha: {maximum_score:.2f}% en el fotograma {suspicious_frame}.",
            (
                f"Muestras sobre el umbral: {len(suspicious_scores)}; "
                f"mínimo requerido: {required_suspicious_frames}."
            ),
            *(
                [
                    "Medianas por checkpoint: "
                    + "; ".join(
                        f"{name}: {score:.2f}% AI"
                        for name, score in per_model_medians.items()
                    ),
                    f"Desacuerdo entre checkpoints: {model_disagreement:.2f} puntos.",
                ]
                if detector_type == "ai" else []
            ),
            "Se descartaron fotogramas no concluyentes antes de la decisión temporal.",
        ],
        raw_label=prediction,
        metadata={
            "total_frames": total_frames,
            "sampled_frames": len(frame_results),
            "valid_frames": len(valid_results),
            "discarded_frames": discarded_frames,
            "fps": round(fps, 2),
            "duration_seconds": round(duration_seconds, 2),
            "maximum_suspicious_score": round(maximum_score, 2),
            "mean_suspicious_score": round(mean_score, 2),
            "median_suspicious_score": round(median_score, 2),
            "suspicious_vote_ratio": round(vote_ratio, 4),
            "suspicious_frame_count": len(suspicious_scores),
            "required_suspicious_frames": required_suspicious_frames,
            "per_model_median_scores": {
                key: round(value, 2) for key, value in per_model_medians.items()
            },
            "model_disagreement_points": round(model_disagreement, 2),
            "quality": {
                "score": round(
                    max(
                        0.0,
                        (len(valid_results) / len(frame_results) * 100.0)
                        - model_disagreement,
                    ),
                    2,
                ),
                "notes": [
                    "La calidad combina cobertura temporal y acuerdo entre checkpoints."
                ],
            },
            "most_suspicious_frame": suspicious_frame,
            "decision_threshold": VIDEO_THRESHOLD,
            "human_threshold": VIDEO_HUMAN_THRESHOLD,
            "minimum_recommended_valid_frames": MIN_VALID_VIDEO_FRAMES,
            "frame_scores": frame_scores,
        },
    )
