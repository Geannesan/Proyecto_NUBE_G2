from app.detector.audio_detector import _build_detection_result
from app.detector.model_loader import AUDIO_AI_MODEL_NAME, AUDIO_DEEPFAKE_MODEL_NAME


def _result(detector_type, fake_score, fake_vote_ratio):
    aggregate = {
        "fake_score": fake_score,
        "real_score": 100.0 - fake_score,
        "fake_vote_ratio": fake_vote_ratio,
        "real_vote_ratio": 1.0 - fake_vote_ratio,
    }

    return _build_detection_result(
        detector_type=detector_type,
        model_name="test-model",
        aggregate=aggregate,
        chunk_results=[{}] * 4,
        audio_metadata={"clipping_ratio": 0.0},
    )


def test_ai_detector_uses_human_label_for_authentic_audio():
    result = _result("ai", fake_score=5.0, fake_vote_ratio=0.0)

    assert result.prediction == "HUMAN"
    assert result.probabilities == {"AI": 5.0, "HUMAN": 95.0}


def test_ai_detector_does_not_flag_borderline_audio_as_ai():
    result = _result("ai", fake_score=94.0, fake_vote_ratio=1.0)

    assert result.prediction == "INCONCLUSIVE"


def test_ai_detector_requires_strong_chunk_agreement():
    result = _result("ai", fake_score=97.0, fake_vote_ratio=0.5)

    assert result.prediction == "INCONCLUSIVE"


def test_ai_detector_flags_only_strong_consistent_evidence():
    result = _result("ai", fake_score=97.0, fake_vote_ratio=1.0)

    assert result.prediction == "AI"


def test_deepfake_detector_keeps_real_label():
    result = _result("deepfake", fake_score=5.0, fake_vote_ratio=0.0)

    assert result.prediction == "REAL"


def test_audio_axes_use_independent_checkpoints():
    assert AUDIO_AI_MODEL_NAME != AUDIO_DEEPFAKE_MODEL_NAME
