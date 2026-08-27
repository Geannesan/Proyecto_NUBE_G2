from app.detector.image_ai_detector import normalize_ai_label
from app.detector.image_deepfake_detector import normalize_deepfake_label


def test_ai_model_abbreviated_human_label_is_normalized():
    assert normalize_ai_label("hum") == "HUMAN"


def test_ai_label_is_normalized():
    assert normalize_ai_label("ai") == "AI"


def test_deepfake_labels_are_normalized():
    assert normalize_deepfake_label("Fake") == "FAKE"
    assert normalize_deepfake_label("Real") == "REAL"
