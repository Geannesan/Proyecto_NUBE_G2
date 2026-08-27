import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.detector.detector import DetectionResult
from app.detector.image_ai_detector import analyze_image_ai
from app.detector.image_deepfake_detector import analyze_image_deepfake


MAX_VIDEO_FRAMES = int(os.getenv("MAX_VIDEO_FRAMES", "16"))
VIDEO_THRESHOLD = float(os.getenv("VIDEO_THRESHOLD", "60"))
MIN_VALID_VIDEO_FRAMES = int(os.getenv("MIN_VALID_VIDEO_FRAMES", "3"))


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
            result = analyze_image_ai(image) if detector_type == "ai" else analyze_image_deepfake(image)
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
    mean_score = float(np.mean(scores))
    median_score = float(np.median(scores))
    maximum_score = float(np.max(scores))
    vote_ratio = float(np.mean(np.asarray(scores) >= VIDEO_THRESHOLD))

    # Median + majority voting prevents one compressed transition from making
    # an otherwise real video a false positive.
    if median_score >= VIDEO_THRESHOLD and vote_ratio >= 0.5:
        prediction, confidence = suspicious_label, median_score
    else:
        prediction, confidence = normal_label, 100.0 - median_score

    suspicious_position = int(np.argmax(scores))
    suspicious_frame = valid_results[suspicious_position][0]
    base_model_name = valid_results[0][1].model_name

    return DetectionResult(
        prediction=prediction,
        confidence=confidence,
        probabilities={suspicious_label: median_score, normal_label: 100.0 - median_score},
        model_name=f"temporal-frame-aggregation:{base_model_name}",
        evidence=[
            f"Se usaron {len(valid_results)} de {len(frame_results)} fotogramas muestreados.",
            f"Mediana de sospecha: {median_score:.2f}%.",
            f"Promedio de sospecha: {mean_score:.2f}%.",
            f"Máxima sospecha: {maximum_score:.2f}% en el fotograma {suspicious_frame}.",
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
            "most_suspicious_frame": suspicious_frame,
            "decision_threshold": VIDEO_THRESHOLD,
            "minimum_recommended_valid_frames": MIN_VALID_VIDEO_FRAMES,
        },
    )
