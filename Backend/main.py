import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import init_db
from app.routes import (
    analyze,
    audio,
    dashboard,
    history,
    image,
    reports,
    video,
)


def get_cors_origins() -> list[str]:
    configured_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    )

    return [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Inicializando base de datos...")

    init_db()

    print("Base de datos inicializada correctamente.")

    yield

    print("Cerrando DeepFakeShield API...")


app = FastAPI(
    title="DeepFakeShield API",
    description=(
        "API para detectar contenido sintético o manipulado "
        "en imágenes, audio y video."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rutas nuevas
app.include_router(image.router)
app.include_router(audio.router)
app.include_router(video.router)
app.include_router(history.router)
app.include_router(dashboard.router)
app.include_router(reports.router)


# Rutas compatibles con el frontend anterior
app.include_router(analyze.router)


@app.get("/")
def root():
    return {
        "service": "DeepFakeShield",
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }