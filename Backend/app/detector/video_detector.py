import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.detector.detector import DetectionResult
from app.detector.image_ai_detector import (
    analyze_image_ai,
)
from app.detector.image_deepfake_detector import (
    analyze_image_deepfake,
)


MAX_VIDEO_FRAMES = int(
    os.getenv("MAX_VIDEO_FRAMES", "12")
)

VIDEO_THRESHOLD = float(
    os.getenv("VIDEO_THRESHOLD", "50")
)


def _suspicious_probability(
    result: DetectionResult,
    detector_type: str,
) -> float:
    suspicious_key = (
        "AI"
        if detector_type == "ai"
        else "FAKE"
    )

    if suspicious_key in result.probabilities:
        return float(
            result.probabilities[suspicious_key]
        )

    if result.prediction == suspicious_key:
        return float(result.confidence)

    return max(
        0.0,
        100.0 - float(result.confidence),
    )


def analyze_video(
    video_path: str | Path,
    detector_type: str = "deepfake",
) -> DetectionResult:
    path = Path(video_path)

    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el video: {path}"
        )

    detector_type = detector_type.strip().lower()

    if detector_type not in {
        "ai",
        "deepfake",
    }:
        raise ValueError(
            "detector_type debe ser 'ai' o 'deepfake'."
        )

    capture = cv2.VideoCapture(str(path))

    if not capture.isOpened():
        raise ValueError(
            "OpenCV no pudo abrir el video."
        )

    try:
        total_frames = int(
            capture.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        fps = float(
            capture.get(cv2.CAP_PROP_FPS)
        )

        if total_frames <= 0:
            raise ValueError(
                "No se pudieron determinar los fotogramas."
            )

        sample_count = min(
            MAX_VIDEO_FRAMES,
            total_frames,
        )

        frame_indexes = np.linspace(
            0,
            total_frames - 1,
            num=sample_count,
            dtype=int,
        )

        frame_results: list[
            tuple[int, DetectionResult]
        ] = []

        for frame_index in frame_indexes:
            capture.set(
                cv2.CAP_PROP_POS_FRAMES,
                int(frame_index),
            )

            success, frame = capture.read()

            if not success or frame is None:
                continue

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            image = Image.fromarray(rgb_frame)

            if detector_type == "ai":
                result = analyze_image_ai(image)
            else:
                result = analyze_image_deepfake(
                    image
                )

            frame_results.append(
                (int(frame_index), result)
            )

    finally:
        capture.release()

    if not frame_results:
        raise ValueError(
            "No se extrajeron fotogramas válidos."
        )

    suspicious_scores = [
        _suspicious_probability(
            result,
            detector_type,
        )
        for _, result in frame_results
    ]

    average_suspicious = float(
        np.mean(suspicious_scores)
    )

    maximum_suspicious = float(
        np.max(suspicious_scores)
    )

    suspicious_label = (
        "AI"
        if detector_type == "ai"
        else "FAKE"
    )

    normal_label = (
        "HUMAN"
        if detector_type == "ai"
        else "REAL"
    )

    if average_suspicious >= VIDEO_THRESHOLD:
        prediction = suspicious_label
        confidence = average_suspicious
    else:
        prediction = normal_label
        confidence = 100.0 - average_suspicious

    suspicious_position = int(
        np.argmax(suspicious_scores)
    )

    suspicious_frame = frame_results[
        suspicious_position
    ][0]

    base_model_name = frame_results[0][1].model_name

    duration_seconds = (
        total_frames / fps
        if fps > 0
        else 0.0
    )

    evidence = [
        f"Se analizaron {len(frame_results)} fotogramas "
        "distribuidos a lo largo del video.",
        f"Promedio de sospecha: {average_suspicious:.2f}%.",
        f"Máxima sospecha: {maximum_suspicious:.2f}% "
        f"en el fotograma {suspicious_frame}.",
        "Este detector usa agregación de fotogramas y no "
        "reemplaza un modelo temporal forense completo.",
    ]

    return DetectionResult(
        prediction=prediction,
        confidence=confidence,
        probabilities={
            suspicious_label: average_suspicious,
            normal_label: 100.0 - average_suspicious,
        },
        model_name=(
            f"frame-aggregation:{base_model_name}"
        ),
        evidence=evidence,
        raw_label=prediction,
        metadata={
            "total_frames": total_frames,
            "sampled_frames": len(frame_results),
            "fps": round(fps, 2),
            "duration_seconds": round(
                duration_seconds,
                2,
            ),
            "maximum_suspicious_score": round(
                maximum_suspicious,
                2,
            ),
            "most_suspicious_frame": suspicious_frame,
        },
    )
