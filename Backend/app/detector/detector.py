from PIL import Image
import torch


from app.detector.model_loader import (
    processor,
    model
)


from app.detector.analyzer import (
    analyze_image
)



def detect_fake(image_path):


    # Abrir imagen

    image = Image.open(
        image_path
    ).convert("RGB")



    # Procesamiento del modelo

    inputs = processor(
        images=image,
        return_tensors="pt"
    )



    # Predicción

    with torch.no_grad():

        outputs = model(
            **inputs
        )



    # Probabilidades

    probs = torch.nn.functional.softmax(
        outputs.logits,
        dim=-1
    )



    predicted = probs.argmax(
        -1
    ).item()



    confidence = (
        probs[0][predicted].item()
        *
        100
    )



    label = model.config.id2label[
        predicted
    ]



    # Nuevo:
    # análisis con OpenCV

    evidence = analyze_image(
        image_path
    )



    return {


        "prediction": label,


        "confidence": round(
            confidence,
            2
        ),


        "analysis": {


            "model_reason":
            "El modelo analizó patrones visuales aprendidos para clasificar la imagen",



            "evidence":
            evidence

        }

    }