import os
from functools import lru_cache
from typing import Any

import torch
from transformers import (
    AutoFeatureExtractor,
    AutoImageProcessor,
    AutoModelForAudioClassification,
    AutoModelForImageClassification,
)


# ============================================================
# MODELOS DE IMAGEN
# ============================================================

IMAGE_AI_MODEL_NAME = os.getenv(
    "IMAGE_AI_MODEL_NAME",
    "Ateeqq/ai-vs-human-image-detector",
)

IMAGE_DEEPFAKE_MODEL_NAME = os.getenv(
    "IMAGE_DEEPFAKE_MODEL_NAME",
    "prithivMLmods/deepfake-detector-model-v1",
)


# ============================================================
# MODELOS DE AUDIO
# ============================================================

# AUDIO + AI:
# voz humana frente a voz generada por IA/TTS/voice cloning.
AUDIO_AI_MODEL_NAME = os.getenv(
    "AUDIO_AI_MODEL_NAME",
    "garystafford/wav2vec2-deepfake-voice-detector",
)

# AUDIO + DEEPFAKE:
# voz auténtica frente a voz falsa/manipulada/spoof.
AUDIO_DEEPFAKE_MODEL_NAME = os.getenv(
    "AUDIO_DEEPFAKE_MODEL_NAME",
    "MelodyMachine/Deepfake-audio-detection-V2",
)


HF_LOCAL_ONLY = (
    os.getenv("HF_LOCAL_ONLY", "false")
    .strip()
    .lower()
    == "true"
)

USE_CUDA = (
    os.getenv("USE_CUDA", "false")
    .strip()
    .lower()
    == "true"
)


def get_device() -> torch.device:
    """
    Devuelve CUDA solamente cuando se solicita y está disponible.
    En caso contrario utiliza CPU.
    """

    if USE_CUDA and torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


def _load_kwargs() -> dict[str, Any]:
    return {
        "local_files_only": HF_LOCAL_ONLY,
    }


def _prepare_image_model(
    model_name: str,
):
    """
    Carga un clasificador visual sin intentar crear tokenizadores
    de texto.
    """

    image_processor = AutoImageProcessor.from_pretrained(
        model_name,
        **_load_kwargs(),
    )

    model = AutoModelForImageClassification.from_pretrained(
        model_name,
        **_load_kwargs(),
    )

    device = get_device()
    model.to(device)
    model.eval()

    return image_processor, model, device


def _prepare_audio_model(
    model_name: str,
):
    """
    Carga únicamente el extractor acústico y el clasificador.
    AutoFeatureExtractor evita depender de un tokenizer de texto.
    """

    feature_extractor = AutoFeatureExtractor.from_pretrained(
        model_name,
        **_load_kwargs(),
    )

    model = AutoModelForAudioClassification.from_pretrained(
        model_name,
        **_load_kwargs(),
    )

    device = get_device()
    model.to(device)
    model.eval()

    return feature_extractor, model, device


@lru_cache(maxsize=1)
def load_image_ai_components():
    return _prepare_image_model(
        IMAGE_AI_MODEL_NAME
    )


@lru_cache(maxsize=1)
def load_image_deepfake_components():
    return _prepare_image_model(
        IMAGE_DEEPFAKE_MODEL_NAME
    )


@lru_cache(maxsize=1)
def load_audio_ai_components():
    return _prepare_audio_model(
        AUDIO_AI_MODEL_NAME
    )


@lru_cache(maxsize=1)
def load_audio_deepfake_components():
    return _prepare_audio_model(
        AUDIO_DEEPFAKE_MODEL_NAME
    )


def load_audio_components():
    """
    Alias de compatibilidad para código antiguo.

    El flujo nuevo debe usar load_audio_ai_components() o
    load_audio_deepfake_components().
    """

    return load_audio_ai_components()