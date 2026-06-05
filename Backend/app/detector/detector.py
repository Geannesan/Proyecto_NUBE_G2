import random

def detect_fake():

    return {
        "prediction": random.choice(
            ["REAL", "FAKE"]
        ),
        "confidence": round(
            random.uniform(80,99),
            2
        )
    }