from PIL import Image
import torch

from app.detector.model_loader import (
    processor,
    model
)

def detect_fake(image_path):

    image = Image.open(
        image_path
    ).convert("RGB")

    inputs = processor(
        images=image,
        return_tensors="pt"
    )

    with torch.no_grad():
        outputs = model(**inputs)

    probs = torch.nn.functional.softmax(
        outputs.logits,
        dim=-1
    )

    predicted = probs.argmax(-1).item()

    confidence = (
        probs[0][predicted].item() * 100
    )

    label = model.config.id2label[
        predicted
    ]

    return {
        "prediction": label,
        "confidence": round(
            confidence,
            2
        )
    }