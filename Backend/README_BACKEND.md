Actualización de modelos de imagen de DeepFakeShield
AI Image Detector
Ruta:
`Backend/app/detector/image_ai_detector.py`
Modelo:
`Ateeqq/ai-vs-human-image-detector`
Clases:
AI
REAL
INCONCLUSIVE
Analiza la imagen completa.
Deepfake Detector
Ruta:
`Backend/app/detector/image_deepfake_detector.py`
Modelo:
`prithivMLmods/AI-vs-Deepfake-vs-Real-Siglip2`
Clases:
AI
DEEPFAKE
REAL
INCONCLUSIVE
Combina el análisis de la imagen completa con recortes faciales.
Archivos que se reemplazan
`Backend/app/detector/model_loader.py`
`Backend/app/detector/image_ai_detector.py`
`Backend/app/detector/image_deepfake_detector.py`
`Backend/app/detector/analyzer.py`
No se crean carpetas nuevas.
Configuración
Copie `ENV_AGREGAR.txt` dentro del archivo `.env` de la raíz.
Reinicio
Desde la raíz del proyecto:
```powershell
docker compose down
docker compose up backend
```
No use `--build` salvo que cambie `requirements.txt`.