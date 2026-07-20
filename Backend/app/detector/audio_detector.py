import os
from collections import defaultdict
from pathlib import Path
from typing import Literal

import librosa
import numpy as np
import torch

from app.detector.detector import DetectionResult
from app.detector.model_loader import (
    AUDIO_AI_MODEL_NAME,
    AUDIO_DEEPFAKE_MODEL_NAME,
    load_audio_ai_components,
    load_audio_deepfake_components,
)


DetectorType = Literal["ai", "deepfake"]


# ============================================================
# CONFIGURACIÓN DE AUDIO
# ============================================================

AUDIO_SAMPLE_RATE = int(
    os.getenv("AUDIO_SAMPLE_RATE", "16000")
)

MAX_AUDIO_SECONDS = float(
    os.getenv("MAX_AUDIO_SECONDS", "60")
)

AUDIO_MIN_SECONDS = float(
    os.getenv("AUDIO_MIN_SECONDS", "2.5")
)

AUDIO_CHUNK_SECONDS = float(
    os.getenv("AUDIO_CHUNK_SECONDS", "5")
)

AUDIO_CHUNK_OVERLAP_SECONDS = float(
    os.getenv(
        "AUDIO_CHUNK_OVERLAP_SECONDS",
        "2.5",
    )
)

AUDIO_MAX_CHUNKS = int(
    os.getenv("AUDIO_MAX_CHUNKS", "8")
)

AUDIO_TRIM_TOP_DB = float(
    os.getenv("AUDIO_TRIM_TOP_DB", "35")
)

AUDIO_AI_THRESHOLD = float(
    os.getenv("AUDIO_AI_THRESHOLD", "82")
)

AUDIO_AI_REAL_THRESHOLD = float(
    os.getenv("AUDIO_AI_REAL_THRESHOLD", "82")
)

AUDIO_DEEPFAKE_THRESHOLD = float(
    os.getenv(
        "AUDIO_DEEPFAKE_THRESHOLD",
        "82",
    )
)

AUDIO_DEEPFAKE_REAL_THRESHOLD = float(
    os.getenv(
        "AUDIO_DEEPFAKE_REAL_THRESHOLD",
        "82",
    )
)

AUDIO_MIN_VOTE_RATIO = float(
    os.getenv("AUDIO_MIN_VOTE_RATIO", "0.60")
)

AUDIO_MAX_CLIPPING_RATIO = float(
    os.getenv(
        "AUDIO_MAX_CLIPPING_RATIO",
        "0.05",
    )
)


# ============================================================
# UTILIDADES DE ETIQUETAS
# ============================================================

def _label_from_config(
    model,
    index: int,
) -> str:
    labels = (
        getattr(model.config, "id2label", {})
        or {}
    )

    return str(
        labels.get(
            index,
            labels.get(
                str(index),
                f"LABEL_{index}",
            ),
        )
    )


def _normalize_audio_label(
    *,
    label: str,
    index: int,
    model_name: str,
) -> str:
    """
    Convierte las etiquetas originales de diferentes checkpoints
    a dos etiquetas internas: FAKE y REAL.
    """

    value = label.strip().lower()

    suspicious_tokens = (
        "fake",
        "spoof",
        "synthetic",
        "generated",
        "deepfake",
        "clone",
        "cloned",
        "ai",
    )

    real_tokens = (
        "real",
        "human",
        "bonafide",
        "bona fide",
        "authentic",
        "genuine",
    )

    if any(
        token in value
        for token in suspicious_tokens
    ):
        return "FAKE"

    if any(
        token in value
        for token in real_tokens
    ):
        return "REAL"

    # Respaldo para el checkpoint de Gary:
    # 0 = real, 1 = fake.
    if model_name == AUDIO_AI_MODEL_NAME:
        return "REAL" if index == 0 else "FAKE"

    # Respaldo para el checkpoint MelodyMachine:
    # 0 = fake, 1 = real.
    if model_name == AUDIO_DEEPFAKE_MODEL_NAME:
        return "FAKE" if index == 0 else "REAL"

    raise ValueError(
        "El modelo devolvió etiquetas que no se pudieron "
        f"interpretar: {label!r}"
    )


# ============================================================
# PREPROCESAMIENTO
# ============================================================

def _load_audio(
    audio_path: str | Path,
) -> tuple[np.ndarray, dict]:
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

    waveform = np.asarray(
        waveform,
        dtype=np.float32,
    )

    if waveform.size == 0:
        raise ValueError(
            "El audio no contiene muestras utilizables."
        )

    waveform = np.nan_to_num(
        waveform,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    original_duration = float(
        waveform.size / sample_rate
    )

    peak = float(
        np.max(np.abs(waveform))
    )

    rms = float(
        np.sqrt(
            np.mean(
                np.square(waveform)
            )
        )
    )

    if peak <= 1e-6 or rms <= 1e-7:
        raise ValueError(
            "El audio está vacío o contiene solamente silencio."
        )

    intervals = librosa.effects.split(
        waveform,
        top_db=AUDIO_TRIM_TOP_DB,
    )

    valid_parts = [
        waveform[start:end]
        for start, end in intervals
        if end > start
    ]

    if not valid_parts:
        raise ValueError(
            "No se detectó voz o sonido suficiente para analizar."
        )

    cleaned_waveform = np.concatenate(
        valid_parts
    ).astype(np.float32)

    analyzed_duration = float(
        cleaned_waveform.size
        / sample_rate
    )

    if analyzed_duration < AUDIO_MIN_SECONDS:
        raise ValueError(
            "El audio útil es demasiado corto. "
            f"Se requieren al menos {AUDIO_MIN_SECONDS:.1f} "
            "segundos de voz clara."
        )

    clipping_ratio = float(
        np.mean(
            np.abs(waveform) >= 0.999
        )
    )

    metadata = {
        "sample_rate": sample_rate,
        "original_duration_seconds": round(
            original_duration,
            2,
        ),
        "analyzed_duration_seconds": round(
            analyzed_duration,
            2,
        ),
        "non_silent_ratio": round(
            analyzed_duration
            / max(original_duration, 1e-6),
            4,
        ),
        "peak_amplitude": round(
            peak,
            6,
        ),
        "rms": round(
            rms,
            6,
        ),
        "clipping_ratio": round(
            clipping_ratio,
            6,
        ),
    }

    return cleaned_waveform, metadata


def _build_chunks(
    waveform: np.ndarray,
) -> list[np.ndarray]:
    """
    Divide el audio en ventanas cortas para evitar que un único
    tramo ruidoso o silencioso domine el resultado.
    """

    chunk_samples = max(
        1,
        int(
            AUDIO_CHUNK_SECONDS
            * AUDIO_SAMPLE_RATE
        ),
    )

    overlap_samples = max(
        0,
        int(
            AUDIO_CHUNK_OVERLAP_SECONDS
            * AUDIO_SAMPLE_RATE
        ),
    )

    stride = max(
        1,
        chunk_samples - overlap_samples,
    )

    if waveform.size <= chunk_samples:
        return [waveform]

    starts = list(
        range(
            0,
            waveform.size
            - chunk_samples
            + 1,
            stride,
        )
    )

    last_start = (
        waveform.size - chunk_samples
    )

    if starts[-1] != last_start:
        starts.append(last_start)

    if len(starts) > AUDIO_MAX_CHUNKS:
        selected_indexes = np.linspace(
            0,
            len(starts) - 1,
            AUDIO_MAX_CHUNKS,
            dtype=int,
        )

        starts = [
            starts[index]
            for index in selected_indexes
        ]

    return [
        waveform[
            start:start + chunk_samples
        ]
        for start in starts
    ]


# ============================================================
# INFERENCIA
# ============================================================

def _predict_chunk(
    *,
    chunk: np.ndarray,
    feature_extractor,
    model,
    device,
    model_name: str,
) -> dict:
    inputs = feature_extractor(
        chunk,
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

    normalized_probabilities: dict[
        str,
        float,
    ] = defaultdict(float)

    raw_probabilities: dict[
        str,
        float,
    ] = {}

    for index, probability in enumerate(
        probabilities_tensor
    ):
        raw_label = _label_from_config(
            model,
            index,
        )

        probability_percent = (
            float(probability.item())
            * 100
        )

        raw_probabilities[
            raw_label
        ] = probability_percent

        normalized_label = (
            _normalize_audio_label(
                label=raw_label,
                index=index,
                model_name=model_name,
            )
        )

        normalized_probabilities[
            normalized_label
        ] += probability_percent

    fake_probability = float(
        normalized_probabilities.get(
            "FAKE",
            0.0,
        )
    )

    real_probability = float(
        normalized_probabilities.get(
            "REAL",
            0.0,
        )
    )

    return {
        "fake_probability": round(
            fake_probability,
            4,
        ),
        "real_probability": round(
            real_probability,
            4,
        ),
        "raw_probabilities": {
            key: round(value, 4)
            for key, value
            in raw_probabilities.items()
        },
    }


def _aggregate_chunks(
    chunk_results: list[dict],
) -> dict:
    fake_values = np.asarray(
        [
            result["fake_probability"]
            for result in chunk_results
        ],
        dtype=np.float64,
    )

    real_values = np.asarray(
        [
            result["real_probability"]
            for result in chunk_results
        ],
        dtype=np.float64,
    )

    # La mediana reduce el impacto de un segmento anómalo.
    fake_score = float(
        0.65 * np.median(fake_values)
        + 0.35 * np.mean(fake_values)
    )

    real_score = float(
        0.65 * np.median(real_values)
        + 0.35 * np.mean(real_values)
    )

    total = fake_score + real_score

    if total > 0:
        fake_score = (
            fake_score / total
            * 100
        )

        real_score = (
            real_score / total
            * 100
        )

    fake_vote_ratio = float(
        np.mean(
            fake_values >= 50.0
        )
    )

    real_vote_ratio = float(
        np.mean(
            real_values > 50.0
        )
    )

    return {
        "fake_score": fake_score,
        "real_score": real_score,
        "fake_vote_ratio": fake_vote_ratio,
        "real_vote_ratio": real_vote_ratio,
        "fake_min": float(
            np.min(fake_values)
        ),
        "fake_max": float(
            np.max(fake_values)
        ),
        "fake_mean": float(
            np.mean(fake_values)
        ),
        "fake_median": float(
            np.median(fake_values)
        ),
    }


def _build_detection_result(
    *,
    detector_type: DetectorType,
    model_name: str,
    aggregate: dict,
    chunk_results: list[dict],
    audio_metadata: dict,
) -> DetectionResult:
    fake_score = float(
        aggregate["fake_score"]
    )

    real_score = float(
        aggregate["real_score"]
    )

    fake_vote_ratio = float(
        aggregate["fake_vote_ratio"]
    )

    real_vote_ratio = float(
        aggregate["real_vote_ratio"]
    )

    if detector_type == "ai":
        suspicious_prediction = "AI"
        suspicious_threshold = (
            AUDIO_AI_THRESHOLD
        )
        real_threshold = (
            AUDIO_AI_REAL_THRESHOLD
        )
        suspicious_description = (
            "voz generada mediante IA, TTS "
            "o clonación de voz"
        )

    else:
        suspicious_prediction = "DEEPFAKE"
        suspicious_threshold = (
            AUDIO_DEEPFAKE_THRESHOLD
        )
        real_threshold = (
            AUDIO_DEEPFAKE_REAL_THRESHOLD
        )
        suspicious_description = (
            "voz falsa, manipulada "
            "o suplantada"
        )

    if (
        fake_score >= suspicious_threshold
        and fake_vote_ratio
        >= AUDIO_MIN_VOTE_RATIO
    ):
        prediction = suspicious_prediction
        confidence = fake_score
        raw_label = "fake"

    elif (
        real_score >= real_threshold
        and real_vote_ratio
        >= AUDIO_MIN_VOTE_RATIO
    ):
        prediction = "REAL"
        confidence = real_score
        raw_label = "real"

    else:
        prediction = "INCONCLUSIVE"
        confidence = max(
            fake_score,
            real_score,
        )
        raw_label = "inconclusive"

    probabilities = {
        suspicious_prediction: fake_score,
        "REAL": real_score,
    }

    evidence = [
        f"Modelo utilizado: {model_name}.",
        f"Se analizaron {len(chunk_results)} "
        f"segmentos de hasta "
        f"{AUDIO_CHUNK_SECONDS:g} segundos.",
        f"Probabilidad combinada de "
        f"{suspicious_description}: "
        f"{fake_score:.2f}%.",
        f"Acuerdo de segmentos sospechosos: "
        f"{fake_vote_ratio * 100:.0f}%.",
        "El audio fue convertido a mono y 16 kHz, "
        "y se eliminaron silencios prolongados.",
    ]

    if prediction == "INCONCLUSIVE":
        evidence.append(
            "La confianza o el acuerdo entre segmentos "
            "no fue suficiente para emitir una "
            "clasificación definitiva."
        )

    if (
        audio_metadata["clipping_ratio"]
        > AUDIO_MAX_CLIPPING_RATIO
    ):
        evidence.append(
            "Se detectó saturación considerable. "
            "Esto puede reducir la precisión."
        )

    metadata = {
        **audio_metadata,
        "detector_type": detector_type,
        "suspicious_threshold": (
            suspicious_threshold
        ),
        "real_threshold": real_threshold,
        "minimum_vote_ratio": (
            AUDIO_MIN_VOTE_RATIO
        ),
        "chunk_seconds": (
            AUDIO_CHUNK_SECONDS
        ),
        "chunk_overlap_seconds": (
            AUDIO_CHUNK_OVERLAP_SECONDS
        ),
        "chunk_count": len(
            chunk_results
        ),
        "aggregate": {
            key: round(
                float(value),
                4,
            )
            for key, value
            in aggregate.items()
        },
        "chunk_results": (
            chunk_results
        ),
    }

    return DetectionResult(
        prediction=prediction,
        confidence=confidence,
        probabilities=probabilities,
        model_name=model_name,
        evidence=evidence,
        raw_label=raw_label,
        metadata=metadata,
    )


def _analyze_audio_with_model(
    *,
    audio_path: str | Path,
    detector_type: DetectorType,
) -> DetectionResult:
    waveform, audio_metadata = (
        _load_audio(audio_path)
    )

    chunks = _build_chunks(
        waveform
    )

    if detector_type == "ai":
        feature_extractor, model, device = (
            load_audio_ai_components()
        )

        model_name = (
            AUDIO_AI_MODEL_NAME
        )

    else:
        feature_extractor, model, device = (
            load_audio_deepfake_components()
        )

        model_name = (
            AUDIO_DEEPFAKE_MODEL_NAME
        )

    chunk_results = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        prediction = _predict_chunk(
            chunk=chunk,
            feature_extractor=feature_extractor,
            model=model,
            device=device,
            model_name=model_name,
        )

        chunk_results.append(
            {
                "chunk_index": index,
                **prediction,
            }
        )

    aggregate = _aggregate_chunks(
        chunk_results
    )

    return _build_detection_result(
        detector_type=detector_type,
        model_name=model_name,
        aggregate=aggregate,
        chunk_results=chunk_results,
        audio_metadata=audio_metadata,
    )


# ============================================================
# FUNCIONES PÚBLICAS
# ============================================================

def analyze_audio_ai(
    audio_path: str | Path,
) -> DetectionResult:
    return _analyze_audio_with_model(
        audio_path=audio_path,
        detector_type="ai",
    )


def analyze_audio_deepfake(
    audio_path: str | Path,
) -> DetectionResult:
    return _analyze_audio_with_model(
        audio_path=audio_path,
        detector_type="deepfake",
    )


def analyze_audio(
    audio_path: str | Path,
    detector_type: DetectorType,
) -> DetectionResult:
    if detector_type == "ai":
        return analyze_audio_ai(
            audio_path
        )

    if detector_type == "deepfake":
        return analyze_audio_deepfake(
            audio_path
        )

    raise ValueError(
        "detector_type de audio debe ser "
        "'ai' o 'deepfake'."
    )