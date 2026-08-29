FROM python:3.11-slim

# Evita archivos .pyc y permite ver los logs inmediatamente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

# Dependencias del sistema para audio, video y OpenCV
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Instalar primero las dependencias para aprovechar la caché
COPY requirements.txt .

ARG PYTORCH_VERSION=2.7.1
ARG TORCHVISION_VERSION=0.22.1
ARG TORCHAUDIO_VERSION=2.7.1

# La imagen estándar es CPU. Evita incluir varios GB de librerías CUDA
# cuando USE_CUDA=false. Para GPU se debe construir una variante NVIDIA.
RUN python -m pip install --upgrade pip \
    && python -m pip install \
      "torch==${PYTORCH_VERSION}" \
      "torchvision==${TORCHVISION_VERSION}" \
      "torchaudio==${TORCHAUDIO_VERSION}" \
      --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install -r requirements.txt

# Copiar el backend
COPY . .

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads /home/app/.cache/huggingface \
    && chown -R appuser:appuser /app /home/app

USER appuser

EXPOSE 8000

# Comando de producción por defecto
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
