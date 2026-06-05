from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File

from app.detector.detector import detect_fake

router = APIRouter()

@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...)
):

    return detect_fake()