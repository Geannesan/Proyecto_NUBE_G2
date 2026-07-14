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


IMAGE_AI_MODEL_NAME = os.getenv(
    "IMAGE_AI_MODEL_NAME",
    "Ateeqq/ai-vs-human-image-detector",
)

IMAGE_DEEPFAKE_MODEL_NAME = os.getenv(
    "IMAGE_DEEPFAKE_MODEL_NAME",
    "prithivMLmods/deepfake-detector-model-v1",
)

AUDIO_DEEPFAKE_MODEL_NAME = os.getenv(
    "AUDIO_DEEPFAKE_MODEL_NAME",
    "garystafford/wav2vec2-deepfake-voice-detector",
)

HF_LOCAL_ONLY = (
    os.getenv("HF_LOCAL_ONLY", "false").lower() == "true"
)

USE_CUDA = (
    os.getenv("USE_CUDA", "true").lower() == "true"
)


def get_device() -> torch.device:
    if USE_CUDA and torch.cuda.is_available():
        return torch.device("cuda")

    return torch.device("cpu")


def _load_kwargs() -> dict[str, Any]:
    return {
        "local_files_only": HF_LOCAL_ONLY,
    }


@lru_cache(maxsize=1)
def load_image_ai_components():
    processor = AutoImageProcessor.from_pretrained(
        IMAGE_AI_MODEL_NAME,
        **_load_kwargs(),
    )

    model = AutoModelForImageClassification.from_pretrained(
        IMAGE_AI_MODEL_NAME,
        **_load_kwargs(),
    )

    device = get_device()
    model.to(device)
    model.eval()

    return processor, model, device


@lru_cache(maxsize=1)
def load_image_deepfake_components():
    processor = AutoImageProcessor.from_pretrained(
        IMAGE_DEEPFAKE_MODEL_NAME,
        **_load_kwargs(),
    )

    model = AutoModelForImageClassification.from_pretrained(
        IMAGE_DEEPFAKE_MODEL_NAME,
        **_load_kwargs(),
    )

    device = get_device()
    model.to(device)
    model.eval()

    return processor, model, device


@lru_cache(maxsize=1)
def load_audio_components():
    feature_extractor = AutoFeatureExtractor.from_pretrained(
        AUDIO_DEEPFAKE_MODEL_NAME,
        **_load_kwargs(),
    )

    model = AutoModelForAudioClassification.from_pretrained(
        AUDIO_DEEPFAKE_MODEL_NAME,
        **_load_kwargs(),
    )

    device = get_device()
    model.to(device)
    model.eval()

    return feature_extractor, model, device
