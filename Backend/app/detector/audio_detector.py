import os
from collections import defaultdict
from pathlib import Path

import librosa
import torch

from app.detector.detector import DetectionResult
from app.detector.model_loader import (
    AUDIO_DEEPFAKE_MODEL_NAME,
    load_audio_components,
)


AUDIO_SAMPLE_RATE = int(
    os.getenv("AUDIO_SAMPLE_RATE", "16000")
)

MAX_AUDIO_SECONDS = float(
    os.getenv("MAX_AUDIO_SECONDS", "30")
)


def _label_from_config(model, index: int) -> str:
    labels = getattr(model.config, "id2label", {}) or {}

    return str(
        labels.get(
            index,
            labels.get(str(index), f"LABEL_{index}"),
        )
    )


def normalize_audio_label(label: str) -> str:
    value = label.strip().lower()

    if any(
        token in value
        for token in (
            "fake",
            "spoof",
            "synthetic",
            "generated",
            "deepfake",
            "ai",
        )
    ):
        return "FAKE"

    if any(
        token in value
        for token in (
            "real",
            "human",
            "bonafide",
            "bona fide",
            "authentic",
            "genuine",
        )
    ):
        return "REAL"

    return label.strip().upper().replace(" ", "_")


def analyze_audio(
    audio_path: str | Path,
) -> DetectionResult:
    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el audio: {path}"
        )

    waveform, sample_rate = librosa.load(
        path,
        sr=AUDIO_SAMPLE_RATE,
        mono=True,
        duration=MAX_AUDIO_SECONDS,
    )

    if waveform.size == 0:
        raise ValueError(
            "El audio no contiene muestras utilizables."
        )

    feature_extractor, model, device = (
        load_audio_components()
    )

    inputs = feature_extractor(
        waveform,
        sampling_rate=AUDIO_SAMPLE_RATE,
        return_tensors="pt",
        padding=True,
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

    prediction = normalize_audio_label(raw_label)

    normalized_probabilities: dict[str, float] = defaultdict(float)

    for index, probability in enumerate(
        probabilities_tensor
    ):
        label = normalize_audio_label(
            _label_from_config(model, index)
        )

        normalized_probabilities[label] += (
            float(probability.item()) * 100
        )

    confidence = float(
        probabilities_tensor[predicted_index].item()
        * 100
    )

    duration_seconds = float(
        waveform.shape[0] / sample_rate
    )

    evidence = [
        "Análisis de características acústicas mediante un "
        "clasificador de voz sintética.",
        f"Se analizaron {duration_seconds:.2f} segundos en mono "
        f"a {sample_rate} Hz.",
        f"Etiqueta original del modelo: {raw_label}.",
    ]

    return DetectionResult(
        prediction=prediction,
        confidence=confidence,
        probabilities=dict(normalized_probabilities),
        model_name=AUDIO_DEEPFAKE_MODEL_NAME,
        evidence=evidence,
        raw_label=raw_label,
        metadata={
            "sample_rate": sample_rate,
            "duration_seconds": round(
                duration_seconds,
                2,
            ),
        },
    )
