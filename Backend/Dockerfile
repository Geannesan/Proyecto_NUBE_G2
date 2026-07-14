FROM python:3.11-slim

# Evita archivos .pyc y permite ver los logs inmediatamente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias del sistema para audio, video y OpenCV
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Instalar primero las dependencias para aprovechar la caché
COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

# Copiar el backend
COPY . .

EXPOSE 8000

# Comando de producción por defecto
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]