from collections import defaultdict

import torch
from PIL import Image

from app.detector.detector import DetectionResult
from app.detector.model_loader import (
    IMAGE_AI_MODEL_NAME,
    load_image_ai_components,
)


def _label_from_config(model, index: int) -> str:
    labels = getattr(model.config, "id2label", {}) or {}

    return str(
        labels.get(
            index,
            labels.get(str(index), f"LABEL_{index}"),
        )
    )


def normalize_ai_label(label: str) -> str:
    value = label.strip().lower()

    if any(
        token in value
        for token in (
            "ai",
            "artificial",
            "generated",
            "synthetic",
            "fake",
        )
    ):
        return "AI"

    if any(
        token in value
        for token in (
            "human",
            "hum",
            "real",
            "natural",
            "authentic",
        )
    ):
        return "HUMAN"

    return label.strip().upper().replace(" ", "_")


def analyze_image_ai(
    image: Image.Image,
) -> DetectionResult:
    processor, model, device = load_image_ai_components()

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

    # Community Forensics usa un único logit: sigmoid(logit) es la
    # probabilidad de imagen generada. Los clasificadores anteriores
    # usaban dos logits y softmax, por lo que se soportan ambos formatos.
    if outputs.logits.shape[-1] == 1:
        ai_probability = float(
            torch.sigmoid(outputs.logits)[0, 0].item()
            * 100
        )
        human_probability = 100.0 - ai_probability
        normalized_probabilities = {
            "AI": ai_probability,
            "HUMAN": human_probability,
        }

        if ai_probability > human_probability:
            prediction = "AI"
            confidence = ai_probability
            raw_label = "generated"
        else:
            prediction = "HUMAN"
            confidence = human_probability
            raw_label = "real"
    else:
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

        prediction = normalize_ai_label(raw_label)
        normalized_probabilities = defaultdict(float)

        for index, probability in enumerate(
            probabilities_tensor
        ):
            label = normalize_ai_label(
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
        "Clasificación mediante un modelo de visión entrenado "
        "para diferenciar imágenes humanas y generadas.",
        f"Etiqueta original del modelo: {raw_label}.",
        "La confianza es una probabilidad del modelo y no una "
        "prueba forense definitiva.",
    ]

    return DetectionResult(
        prediction=prediction,
        confidence=confidence,
        probabilities=dict(normalized_probabilities),
        model_name=IMAGE_AI_MODEL_NAME,
        evidence=evidence,
        raw_label=raw_label,
        metadata={
            "image_width": rgb_image.width,
            "image_height": rgb_image.height,
        },
    )
