import numpy as np

from app.detector.detector import DetectionResult
from app.detector.video_detector import (
    _is_valid_result,
    _required_suspicious_frames,
    _sample_frame_indexes,
    _suspicious_probability,
)
from app.detector.model_loader import VIDEO_AI_MODEL_NAME, VIDEO_DEEPFAKE_MODEL_NAME


def _result(prediction: str, probabilities: dict[str, float]) -> DetectionResult:
    return DetectionResult(
        prediction=prediction,
        confidence=max(probabilities.values(), default=0.0),
        probabilities=probabilities,
        model_name="test-model",
    )


def test_inconclusive_deepfake_frame_is_discarded():
    result = _result("INCONCLUSIVE", {"FAKE": 0.0, "REAL": 0.0})
    assert not _is_valid_result(result, "deepfake")


def test_real_frame_keeps_low_fake_probability():
    result = _result("REAL", {"FAKE": 7.0, "REAL": 93.0})
    assert _is_valid_result(result, "deepfake")
    assert _suspicious_probability(result, "deepfake") == 7.0


def test_sampling_avoids_first_and_last_frame():
    indexes = _sample_frame_indexes(100, 10)
    assert np.array_equal(indexes, np.asarray([5, 15, 25, 35, 45, 55, 65, 75, 85, 95]))


def test_video_uses_dedicated_models():
    assert VIDEO_AI_MODEL_NAME == "umm-maybe/AI-image-detector"
    assert VIDEO_DEEPFAKE_MODEL_NAME == "prithivMLmods/Deep-Fake-Detector-v2-Model"


def test_partial_manipulation_requires_multiple_suspicious_frames():
    assert _required_suspicious_frames(20) == 2


def test_required_suspicious_frames_scales_with_longer_sampling():
    assert _required_suspicious_frames(100) == 10
