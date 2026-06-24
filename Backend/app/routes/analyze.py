import os
import uuid


from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi import HTTPException


from app.detector.detector import detect_fake



router = APIRouter()



@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...)
):


    # validar imagen

    if not file.content_type.startswith("image"):

        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser una imagen"
        )



    # crear carpeta

    os.makedirs(
        "uploads",
        exist_ok=True
    )



    # nombre único

    file_path = (
        f"uploads/{uuid.uuid4()}_{file.filename}"
    )



    # guardar imagen

    with open(
        file_path,
        "wb"
    ) as buffer:


        buffer.write(
            await file.read()
        )



    # enviar al modelo

    result = detect_fake(
        file_path
    )



    return result