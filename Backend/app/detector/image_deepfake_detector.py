import os
from collections import defaultdict
from typing import Any

import cv2
import numpy as np
import torch
from PIL import Image, ImageOps

from app.detector.detector import DetectionResult
from app.detector.model_loader import (
    IMAGE_DEEPFAKE_MODEL_NAME,
    load_image_deepfake_components,
)


# Valores iniciales de ingeniería.
# Deben calibrarse después con un conjunto propio de imágenes reales y fake.
MIN_FACE_SIDE = int(
    os.getenv("DEEPFAKE_MIN_FACE_SIDE", "160")
)
MIN_FACE_RATIO = float(
    os.getenv("DEEPFAKE_MIN_FACE_RATIO", "0.05")
)
MIN_BLUR_SCORE = float(
    os.getenv("DEEPFAKE_MIN_BLUR_SCORE", "55")
)
FAKE_THRESHOLD = float(
    os.getenv("DEEPFAKE_FAKE_THRESHOLD", "98")
)
REAL_THRESHOLD = float(
    os.getenv("DEEPFAKE_REAL_THRESHOLD", "85")
)


def _label_from_config(model, index: int) -> str:
    labels = getattr(model.config, "id2label", {}) or {}

    return str(
        labels.get(
            index,
            labels.get(str(index), f"LABEL_{index}"),
        )
    )


def normalize_deepfake_label(label: str) -> str:
    value = label.strip().lower()

    if any(
        token in value
        for token in (
            "fake",
            "deepfake",
            "manipulated",
            "synthetic",
            "spoof",
        )
    ):
        return "FAKE"

    if any(
        token in value
        for token in (
            "real",
            "human",
            "authentic",
            "bonafide",
            "bona fide",
        )
    ):
        return "REAL"

    return label.strip().upper().replace(" ", "_")


def _build_inconclusive_result(
    *,
    image: Image.Image,
    reason: str,
    metadata: dict[str, Any],
    probabilities: dict[str, float] | None = None,
    confidence: float = 0.0,
) -> DetectionResult:
    final_probabilities = probabilities or {
        "FAKE": 0.0,
        "REAL": 0.0,
    }

    return DetectionResult(
        prediction="INCONCLUSIVE",
        confidence=confidence,
        probabilities=final_probabilities,
        model_name=IMAGE_DEEPFAKE_MODEL_NAME,
        evidence=[
            reason,
            "Use una fotografía original, nítida y con un solo "
            "rostro visible en primer plano.",
            "Un resultado no concluyente evita clasificar como fake "
            "una entrada que no cumple las condiciones mínimas.",
        ],
        raw_label="inconclusive",
        metadata={
            "image_width": image.width,
            "image_height": image.height,
            "quality_ok": False,
            "quality_reason": reason,
            **metadata,
        },
    )


def _prepare_face(
    image: Image.Image,
) -> tuple[Image.Image | None, dict[str, Any], str | None]:
    rgb_image = ImageOps.exif_transpose(image).convert("RGB")
    rgb_array = np.asarray(rgb_image)

    gray = cv2.cvtColor(
        rgb_array,
        cv2.COLOR_RGB2GRAY,
    )

    cascade_path = (
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )

    face_detector = cv2.CascadeClassifier(cascade_path)

    if face_detector.empty():
        return (
            None,
            {
                "faces_detected": 0,
                "cascade_path": cascade_path,
            },
            "No se pudo inicializar el detector facial de OpenCV.",
        )

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    metadata: dict[str, Any] = {
        "faces_detected": int(len(faces)),
    }

    if len(faces) == 0:
        return (
            None,
            metadata,
            "No se detectó un rostro frontal suficientemente visible.",
        )

    if len(faces) > 1:
        return (
            None,
            metadata,
            "Se detectaron varios rostros. Analice cada rostro "
            "por separado para reducir falsos positivos.",
        )

    x, y, width, height = [
        int(value)
        for value in faces[0]
    ]

    face_ratio = (
        float(width * height)
        / float(rgb_image.width * rgb_image.height)
    )

    metadata.update(
        {
            "face_x": x,
            "face_y": y,
            "face_width": width,
            "face_height": height,
            "face_ratio": round(face_ratio, 4),
        }
    )

    if min(width, height) < MIN_FACE_SIDE:
        return (
            None,
            metadata,
            "El rostro detectado es demasiado pequeño. Use una "
            "imagen donde el rostro mida al menos "
            f"{MIN_FACE_SIDE} píxeles por lado.",
        )

    if face_ratio < MIN_FACE_RATIO:
        return (
            None,
            metadata,
            "El rostro ocupa una parte demasiado pequeña de la imagen. "
            "Recorte la fotografía alrededor del rostro.",
        )

    margin = int(max(width, height) * 0.25)

    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(rgb_image.width, x + width + margin)
    y2 = min(rgb_image.height, y + height + margin)

    face_crop = rgb_image.crop(
        (x1, y1, x2, y2)
    )

    face_gray = cv2.cvtColor(
        np.asarray(face_crop),
        cv2.COLOR_RGB2GRAY,
    )

    blur_score = float(
        cv2.Laplacian(
            face_gray,
            cv2.CV_64F,
        ).var()
    )

    metadata.update(
        {
            "face_crop_width": face_crop.width,
            "face_crop_height": face_crop.height,
            "blur_score": round(blur_score, 2),
        }
    )

    if blur_score < MIN_BLUR_SCORE:
        return (
            None,
            metadata,
            "El rostro está borroso o tiene pocos detalles. "
            "Use una fotografía más nítida.",
        )

    metadata["quality_ok"] = True
    metadata["quality_reason"] = "Calidad facial suficiente."

    return face_crop, metadata, None


def _create_variants(
    face_image: Image.Image,
) -> list[tuple[str, Image.Image]]:
    width, height = face_image.size

    crop_margin_x = int(width * 0.05)
    crop_margin_y = int(height * 0.05)

    center_crop = face_image.crop(
        (
            crop_margin_x,
            crop_margin_y,
            width - crop_margin_x,
            height - crop_margin_y,
        )
    )

    flipped = face_image.transpose(
        Image.Transpose.FLIP_LEFT_RIGHT
    )

    return [
        ("face", face_image),
        ("face_flipped", flipped),
        ("face_center_crop", center_crop),
    ]


def _predict_probabilities(
    *,
    image: Image.Image,
    processor,
    model,
    device,
) -> tuple[dict[str, float], str]:
    inputs = processor(
        images=image,
        return_tensors="pt",
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.inference_mode():
        outputs = model(**inputs)

    probabilities_tensor = torch.softmax(
        outputs.logits,
        dim=-1,
    )[0]

    predicted_index = int(
        probabilities_tensor.argmax().item()
    )

    raw_label = _label_from_config(
        model,
        predicted_index,
    )

    normalized_probabilities: dict[str, float] = defaultdict(float)

    for index, probability in enumerate(
        probabilities_tensor
    ):
        label = normalize_deepfake_label(
            _label_from_config(model, index)
        )

        normalized_probabilities[label] += (
            float(probability.item()) * 100
        )

    return dict(normalized_probabilities), raw_label


def analyze_image_deepfake(
    image: Image.Image,
) -> DetectionResult:
    rgb_image = ImageOps.exif_transpose(
        image
    ).convert("RGB")

    face_image, quality_metadata, quality_error = (
        _prepare_face(rgb_image)
    )

    if face_image is None:
        return _build_inconclusive_result(
            image=rgb_image,
            reason=(
                quality_error
                or "La imagen no cumple las condiciones mínimas."
            ),
            metadata=quality_metadata,
        )

    processor, model, device = (
        load_image_deepfake_components()
    )

    variant_results: list[dict[str, Any]] = []

    for variant_name, variant_image in _create_variants(
        face_image
    ):
        probabilities, raw_label = _predict_probabilities(
            image=variant_image,
            processor=processor,
            model=model,
            device=device,
        )

        variant_results.append(
            {
                "variant": variant_name,
                "raw_label": raw_label,
                "FAKE": float(
                    probabilities.get("FAKE", 0.0)
                ),
                "REAL": float(
                    probabilities.get("REAL", 0.0)
                ),
            }
        )

    fake_values = [
        result["FAKE"]
        for result in variant_results
    ]
    real_values = [
        result["REAL"]
        for result in variant_results
    ]

    average_fake = float(np.mean(fake_values))
    average_real = float(np.mean(real_values))

    fake_votes = sum(
        value_fake > value_real
        for value_fake, value_real
        in zip(fake_values, real_values)
    )

    real_votes = len(variant_results) - fake_votes

    probabilities = {
        "FAKE": average_fake,
        "REAL": average_real,
    }

    metadata = {
        "image_width": rgb_image.width,
        "image_height": rgb_image.height,
        **quality_metadata,
        "quality_ok": True,
        "quality_reason": "Calidad facial suficiente.",
        "fake_threshold": FAKE_THRESHOLD,
        "real_threshold": REAL_THRESHOLD,
        "variant_results": variant_results,
        "fake_votes": fake_votes,
        "real_votes": real_votes,
    }

    if (
        average_fake >= FAKE_THRESHOLD
        and fake_votes == len(variant_results)
    ):
        prediction = "FAKE"
        confidence = average_fake
        raw_label = "fake"

        evidence = [
            "Se detectó un único rostro con calidad suficiente.",
            "Las tres variantes del rostro coincidieron en la "
            "clasificación FAKE.",
            f"Probabilidad media FAKE: {average_fake:.2f}%.",
            "La salida sigue siendo probabilística y no constituye "
            "una prueba forense definitiva.",
        ]

    elif (
        average_real >= REAL_THRESHOLD
        and real_votes >= 2
    ):
        prediction = "REAL"
        confidence = average_real
        raw_label = "real"

        evidence = [
            "Se detectó un único rostro con calidad suficiente.",
            "La mayoría de las variantes coincidió en la "
            "clasificación REAL.",
            f"Probabilidad media REAL: {average_real:.2f}%.",
            "La salida sigue siendo probabilística y no constituye "
            "una prueba forense definitiva.",
        ]

    else:
        reason = (
            "Las variantes analizadas no alcanzaron un consenso "
            "suficiente para clasificar la imagen como REAL o FAKE."
        )

        return _build_inconclusive_result(
            image=rgb_image,
            reason=reason,
            metadata=metadata,
            probabilities=probabilities,
            confidence=max(
                average_fake,
                average_real,
            ),
        )

    return DetectionResult(
        prediction=prediction,
        confidence=confidence,
        probabilities=probabilities,
        model_name=IMAGE_DEEPFAKE_MODEL_NAME,
        evidence=evidence,
        raw_label=raw_label,
        metadata=metadata,
    )