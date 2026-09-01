from app.detector.image_ai_detector import normalize_ai_label
from app.detector.image_deepfake_detector import (
    _classify_probabilities,
    _has_fake_consensus,
    _select_primary_face,
    normalize_deepfake_label,
)


def test_ai_model_abbreviated_human_label_is_normalized():
    assert normalize_ai_label("hum") == "HUMAN"


def test_ai_label_is_normalized():
    assert normalize_ai_label("ai") == "AI"


def test_deepfake_labels_are_normalized():
    assert normalize_deepfake_label("Fake") == "FAKE"
    assert normalize_deepfake_label("Real") == "REAL"


def test_real_probability_above_default_threshold_is_classified():
    assert _classify_probabilities(32.3, 67.7) == (
        "REAL",
        "Real",
        67.7,
    )


def test_near_tie_remains_inconclusive():
    assert _classify_probabilities(55.0, 45.0) is None


def test_only_the_winning_class_can_be_selected(monkeypatch):
    monkeypatch.setattr(
        "app.detector.image_deepfake_detector.FAKE_THRESHOLD",
        40.0,
    )
    monkeypatch.setattr(
        "app.detector.image_deepfake_detector.REAL_THRESHOLD",
        60.0,
    )

    assert _classify_probabilities(45.0, 55.0) is None


def test_largest_face_is_selected_when_it_is_dominant():
    face, ratio = _select_primary_face(
        [(954, 1216, 178, 178), (235, 994, 745, 745)]
    )

    assert face == (235, 994, 745, 745)
    assert ratio is not None and ratio > 17


def test_similar_sized_faces_require_separate_analysis():
    face, ratio = _select_primary_face(
        [(10, 10, 200, 200), (250, 10, 180, 180)]
    )

    assert face is None
    assert ratio is not None and ratio < 2


def test_single_face_uses_configured_fake_threshold():
    assert _has_fake_consensus([{"FAKE": 75.42, "REAL": 24.58}])


def test_group_requires_repeated_or_very_strong_fake_evidence():
    assert not _has_fake_consensus([
        {"FAKE": 75.42, "REAL": 24.58},
        {"FAKE": 20.0, "REAL": 80.0},
    ])
    assert _has_fake_consensus([
        {"FAKE": 75.42, "REAL": 24.58},
        {"FAKE": 70.0, "REAL": 30.0},
    ])
