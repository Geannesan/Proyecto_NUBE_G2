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
MIN_PRIMARY_FACE_AREA_RATIO = float(
    os.getenv("DEEPFAKE_MIN_PRIMARY_FACE_AREA_RATIO", "2.0")
)
FAKE_THRESHOLD = float(
    os.getenv("DEEPFAKE_FAKE_THRESHOLD", "60")
)
REAL_THRESHOLD = float(
    os.getenv("DEEPFAKE_REAL_THRESHOLD", "60")
)
MAX_GROUP_FACES = int(os.getenv("DEEPFAKE_MAX_GROUP_FACES", "12"))
GROUP_MIN_FACE_SIDE = int(os.getenv("DEEPFAKE_GROUP_MIN_FACE_SIDE", "80"))
GROUP_MIN_BLUR_SCORE = float(os.getenv("DEEPFAKE_GROUP_MIN_BLUR_SCORE", "35"))


def _classify_probabilities(
    fake_probability: float,
    real_probability: float,
) -> tuple[str, str, float] | None:
    """Return a verdict only when the winning class clears its threshold.

    Checking the winning class prevents asymmetric thresholds from selecting a
    lower-probability label.  The 60% defaults leave a narrow abstention band
    around an essentially tied binary prediction and remain configurable until
    project-specific calibration data is available.
    """
    if (
        fake_probability > real_probability
        and fake_probability >= FAKE_THRESHOLD
    ):
        return "FAKE", "Fake", fake_probability

    if (
        real_probability > fake_probability
        and real_probability >= REAL_THRESHOLD
    ):
        return "REAL", "Real", real_probability

    return None


def _has_fake_consensus(face_results: list[dict[str, Any]]) -> bool:
    """Apply the normal threshold to a portrait and stricter rules to groups."""
    fake_faces = [item for item in face_results if item["FAKE"] >= FAKE_THRESHOLD]
    if not fake_faces:
        return False
    if len(face_results) == 1:
        return True
    strongest_fake = max(item["FAKE"] for item in fake_faces)
    return len(fake_faces) >= 2 or strongest_fake >= 85.0


def _select_primary_face(
    faces: Any,
) -> tuple[tuple[int, int, int, int] | None, float | None]:
    ordered = sorted(
        (tuple(int(value) for value in face) for face in faces),
        key=lambda face: face[2] * face[3],
        reverse=True,
    )

    if not ordered:
        return None, None
    if len(ordered) == 1:
        return ordered[0], None

    largest_area = float(ordered[0][2] * ordered[0][3])
    second_area = float(ordered[1][2] * ordered[1][3])
    dominance_ratio = largest_area / max(second_area, 1.0)

    if dominance_ratio < MIN_PRIMARY_FACE_AREA_RATIO:
        return None, dominance_ratio

    return ordered[0], dominance_ratio


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

    primary_face, dominance_ratio = _select_primary_face(faces)

    if dominance_ratio is not None:
        metadata["primary_face_area_ratio"] = round(dominance_ratio, 2)
        metadata["primary_face_selection_threshold"] = (
            MIN_PRIMARY_FACE_AREA_RATIO
        )

    if primary_face is None:
        return (
            None,
            metadata,
            "Se detectaron varios rostros de tamaño similar. Analice cada "
            "rostro por separado para reducir falsos positivos.",
        )

    x, y, width, height = [
        int(value)
        for value in primary_face
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
            "primary_face_selected": len(faces) > 1,
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


def _prepare_face_set(
    image: Image.Image,
) -> tuple[list[tuple[Image.Image, dict[str, Any]]], dict[str, Any], str | None]:
    """Prepara varios rostros para fotografías grupales."""
    rgb_image = ImageOps.exif_transpose(image).convert("RGB")
    gray = cv2.cvtColor(np.asarray(rgb_image), cv2.COLOR_RGB2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        return [], {"faces_detected": 0, "cascade_path": cascade_path}, "No se pudo inicializar el detector facial de OpenCV."
    detected = detector.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5,
        minSize=(GROUP_MIN_FACE_SIDE, GROUP_MIN_FACE_SIDE),
    )
    ordered = sorted(
        (tuple(int(value) for value in face) for face in detected),
        key=lambda face: face[2] * face[3], reverse=True,
    )[:MAX_GROUP_FACES]
    prepared: list[tuple[Image.Image, dict[str, Any]]] = []
    rejected: list[dict[str, Any]] = []
    required_face_side = MIN_FACE_SIDE if len(ordered) == 1 else GROUP_MIN_FACE_SIDE
    for index, (x, y, width, height) in enumerate(ordered):
        margin = int(max(width, height) * 0.25)
        crop = rgb_image.crop((
            max(0, x - margin), max(0, y - margin),
            min(rgb_image.width, x + width + margin),
            min(rgb_image.height, y + height + margin),
        ))
        crop_gray = cv2.cvtColor(np.asarray(crop), cv2.COLOR_RGB2GRAY)
        blur_score = float(cv2.Laplacian(crop_gray, cv2.CV_64F).var())
        details = {
            "face_index": index + 1, "x": x, "y": y,
            "width": width, "height": height,
            "area_percent": round(width * height / max(1, rgb_image.width * rgb_image.height) * 100, 2),
            "blur_score": round(blur_score, 2),
        }
        if min(width, height) < required_face_side:
            rejected.append({
                **details,
                "reason": "face_too_small",
                "minimum_face_side": required_face_side,
            })
        elif blur_score < GROUP_MIN_BLUR_SCORE:
            rejected.append({**details, "reason": "low_detail"})
        else:
            prepared.append((crop, details))
    metadata = {
        "faces_detected": len(ordered), "faces_evaluable": len(prepared),
        "faces_rejected": rejected, "group_face_limit": MAX_GROUP_FACES,
    }
    if not ordered:
        return [], metadata, "No se detectó un rostro frontal suficientemente visible."
    if not prepared:
        return [], metadata, "Se detectaron rostros, pero ninguno conservó detalle suficiente para la inferencia."
    return prepared, metadata, None


def analyze_image_deepfake(
    image: Image.Image,
) -> DetectionResult:
    rgb_image = ImageOps.exif_transpose(
        image
    ).convert("RGB")

    face_set, face_metadata, quality_error = _prepare_face_set(rgb_image)

    if not face_set:
        return _build_inconclusive_result(
            image=rgb_image,
            reason=quality_error or "No existe evidencia facial evaluable.",
            metadata=face_metadata,
        )

    processor, model, device = (
        load_image_deepfake_components()
    )

    face_results: list[dict[str, Any]] = []
    for face_crop, face_details in face_set:
        variants: list[dict[str, Any]] = []
        for variant_name, variant in _create_variants(face_crop):
            variant_probabilities, variant_raw_label = _predict_probabilities(
                image=variant, processor=processor, model=model, device=device,
            )
            variants.append({
                "variant": variant_name, "raw_label": variant_raw_label,
                "FAKE": float(variant_probabilities.get("FAKE", 0.0)),
                "REAL": float(variant_probabilities.get("REAL", 0.0)),
            })
        face_results.append({
            **face_details,
            "FAKE": round(float(np.mean([item["FAKE"] for item in variants])), 4),
            "REAL": round(float(np.mean([item["REAL"] for item in variants])), 4),
            "variants": variants,
        })

    real_faces = [item for item in face_results if item["REAL"] >= REAL_THRESHOLD]
    strongest_fake = max((item["FAKE"] for item in face_results), default=0.0)
    real_agreement = len(real_faces) / max(1, len(face_results))
    fake_decision = _has_fake_consensus(face_results)
    if fake_decision:
        average_fake = strongest_fake
        average_real = 100.0 - average_fake
        decision = ("FAKE", "Fake", average_fake)
    else:
        average_real = float(np.mean([item["REAL"] for item in face_results]))
        average_fake = 100.0 - average_real
        decision = (
            ("REAL", "Real", average_real)
            if real_agreement >= 0.6 and average_real >= REAL_THRESHOLD
            else None
        )
    probabilities = {"FAKE": average_fake, "REAL": average_real}

    if decision is None:
        return _build_inconclusive_result(
            image=rgb_image,
            reason=(
                "Las probabilidades de manipulación y contenido real están "
                "en una zona de incertidumbre; no alcanzan los umbrales "
                "calibrables para emitir un veredicto."
            ),
            metadata={
                **face_metadata,
                "inference_strategy": "multi_face_multi_view_thresholded",
                "face_results": face_results,
                "real_face_agreement_percent": round(real_agreement * 100, 2),
                "fake_threshold": FAKE_THRESHOLD,
                "real_threshold": REAL_THRESHOLD,
            },
            probabilities=probabilities,
            confidence=max(average_fake, average_real),
        )

    prediction, raw_label, confidence = decision

    evidence = [
        f"Se evaluaron {len(face_results)} de {face_metadata['faces_detected']} rostros detectados.",
        "Cada rostro se contrastó en tres variantes para comprobar la estabilidad de la predicción.",
        f"Acuerdo de rostros clasificados como reales: {real_agreement * 100:.2f}%.",
        f"Probabilidad media {prediction}: {confidence:.2f}%.",
        "La salida es probabilística y no constituye una prueba "
        "forense definitiva.",
    ]

    metadata = {
        "image_width": rgb_image.width,
        "image_height": rgb_image.height,
        **face_metadata,
        "quality_ok": True,
        "quality_reason": f"{len(face_results)} rostros con detalle suficiente.",
        "inference_strategy": "multi_face_multi_view_thresholded",
        "face_results": face_results,
        "real_face_agreement_percent": round(real_agreement * 100, 2),
        "fake_threshold": FAKE_THRESHOLD,
        "real_threshold": REAL_THRESHOLD,
    }

    return DetectionResult(
        prediction=prediction,
        confidence=confidence,
        probabilities=probabilities,
        model_name=IMAGE_DEEPFAKE_MODEL_NAME,
        evidence=evidence,
        raw_label=raw_label,
        metadata=metadata,
    )
