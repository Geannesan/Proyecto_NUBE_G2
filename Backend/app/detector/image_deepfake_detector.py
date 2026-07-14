from collections import defaultdict

import torch
from PIL import Image

from app.detector.detector import DetectionResult
from app.detector.model_loader import (
    IMAGE_DEEPFAKE_MODEL_NAME,
    load_image_deepfake_components,
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


def analyze_image_deepfake(
    image: Image.Image,
) -> DetectionResult:
    processor, model, device = (
        load_image_deepfake_components()
    )

    rgb_image = image.convert("RGB")

    inputs = processor(
        images=rgb_image,
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

    prediction = normalize_deepfake_label(raw_label)

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

    confidence = float(
        probabilities_tensor[predicted_index].item()
        * 100
    )

    evidence = [
        "Clasificación de patrones visuales asociados con "
        "manipulación o deepfake.",
        f"Etiqueta original del modelo: {raw_label}.",
        "La compresión, iluminación, resolución y tamaño del "
        "rostro pueden afectar el resultado.",
    ]

    return DetectionResult(
        prediction=prediction,
        confidence=confidence,
        probabilities=dict(normalized_probabilities),
        model_name=IMAGE_DEEPFAKE_MODEL_NAME,
        evidence=evidence,
        raw_label=raw_label,
        metadata={
            "image_width": rgb_image.width,
            "image_height": rgb_image.height,
        },
    )
