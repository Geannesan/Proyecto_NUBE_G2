from transformers import AutoImageProcessor
from transformers import AutoModelForImageClassification
from PIL import Image
import torch

MODEL_NAME = "Ateeqq/ai-vs-human-image-detector"

print("Paso 1")

processor = AutoImageProcessor.from_pretrained(MODEL_NAME)

print("Paso 2")

model = AutoModelForImageClassification.from_pretrained(MODEL_NAME)

print("Paso 3")

print(model.config.id2label)

image = Image.open("ejemplo.jpg").convert("RGB")

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

predicted_class = probs.argmax(-1).item()

confidence = probs[0][predicted_class].item() * 100

print(
    "Etiqueta:",
    model.config.id2label[predicted_class]
)

print(
    "Confianza:",
    round(confidence, 2),
    "%"
)