from app.scripts.evaluate_predictions import evaluate


def test_perfect_predictions_have_perfect_metrics():
    rows = [
        {"ground_truth": "0", "score": "5"},
        {"ground_truth": "0", "score": "10"},
        {"ground_truth": "1", "score": "90"},
        {"ground_truth": "1", "score": "95"},
    ]
    metrics = evaluate(rows)
    assert metrics["accuracy"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["confusion_matrix"] == {"tp": 2, "tn": 2, "fp": 0, "fn": 0}
