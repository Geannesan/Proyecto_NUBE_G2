from transformers import AutoImageProcessor
from transformers import AutoModelForImageClassification

MODEL_NAME = "Ateeqq/ai-vs-human-image-detector"

print("Cargando modelo...")

processor = AutoImageProcessor.from_pretrained(
    MODEL_NAME
)

model = AutoModelForImageClassification.from_pretrained(
    MODEL_NAME
)

print("Modelo cargado")