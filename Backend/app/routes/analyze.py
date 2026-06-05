import os

from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File

from app.detector.detector import detect_fake

router = APIRouter()

@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...)
):

    os.makedirs(
        "uploads",
        exist_ok=True
    )

    file_path = (
        f"uploads/{file.filename}"
    )

    with open(
        file_path,
        "wb"
    ) as buffer:

        buffer.write(
            await file.read()
        )

    result = detect_fake(
        file_path
    )

    return result