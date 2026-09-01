import os
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import transforms
from torchvision.models import efficientnet_b0

from app.detector.detector import DetectionResult
from app.detector.model_loader import (
    IMAGE_AI_MODEL_NAME,
    load_image_ai_components,
)


AI_EDITED_MODEL_PATH = Path(os.getenv(
    "AI_EDITED_MODEL_PATH", "training_data/models/candidate_ai_edited.pt"
))
AI_EDITED_MIN_PROMOTION_PAIRS = int(os.getenv("AI_EDITED_MIN_PROMOTION_PAIRS", "30"))


@lru_cache(maxsize=1)
def _load_ai_edited_candidate():
    if not AI_EDITED_MODEL_PATH.exists():
        return None
    checkpoint = torch.load(AI_EDITED_MODEL_PATH, map_location="cpu", weights_only=True)
    model = efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    transform = transforms.Compose([
        transforms.Resize((288, 288)),
        transforms.CenterCrop(256),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    return model, transform, checkpoint


def _run_ai_edited_candidate(image: Image.Image) -> dict | None:
    loaded = _load_ai_edited_candidate()
    if loaded is None:
        return None
    model, transform, checkpoint = loaded
    with torch.inference_mode():
        probabilities = torch.softmax(model(transform(image).unsqueeze(0)), dim=1)[0]
    edited_probability = float(probabilities[1].item() * 100.0)
    real_probability = float(probabilities[0].item() * 100.0)
    total_pairs = int(checkpoint.get("training_pairs", 0)) + int(checkpoint.get("validation_pairs", 0))
    return {
        "status": "shadow" if total_pairs < AI_EDITED_MIN_PROMOTION_PAIRS else "eligible_for_evaluation",
        "prediction": "AI_EDITED" if edited_probability >= real_probability else "REAL",
        "probabilities": {"AI_EDITED": edited_probability, "REAL": real_probability},
        "validation_accuracy": float(checkpoint.get("validation_accuracy", 0.0) * 100.0),
        "training_pairs": int(checkpoint.get("training_pairs", 0)),
        "validation_pairs": int(checkpoint.get("validation_pairs", 0)),
        "minimum_promotion_pairs": AI_EDITED_MIN_PROMOTION_PAIRS,
        "decision_contribution": False,
        "model": "EfficientNet-B0 REAL_vs_AI_EDITED candidate",
    }


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
    ai_edited_candidate = _run_ai_edited_candidate(rgb_image)

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
    if ai_edited_candidate:
        evidence.append(
            "El candidato REAL vs AI_EDITED se ejecutó en modo shadow; "
            "su score se registra, pero todavía no modifica el veredicto."
        )

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
            "ai_edited_candidate": ai_edited_candidate,
        },
    )
