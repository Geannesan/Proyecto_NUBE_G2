# Backend DeepFakeShield

## Rutas

- `POST /api/v1/image/analyze`
- `POST /api/v1/audio/analyze`
- `POST /api/v1/video/analyze`

Campos multipart: `file` y `detector_type`, con valores `ai`, `deepfake` o `comprehensive`.

También están disponibles dashboard, historial y reportes en `/api/v1/dashboard`, `/api/v1/history` y `/api/v1/reports/{analysis_id}`.

## Análisis integral

`comprehensive` ejecuta generación AI y manipulación/deepfake como ejes independientes. En video también extrae la pista de audio con FFmpeg. Las señales vocales y visuales permanecen separadas hasta disponer de calibración audiovisual.

Cada registro incluye probabilidades, evidencias, modelos, calidad técnica, SHA-256, Content Credentials mediante C2PA y métricas de validación disponibles.

Los PDF se generan bajo demanda en memoria y se envían como descarga. No se guardan dentro de `Backend/reports` ni se versionan en Git.

## Etiquetas

- `HUMAN`: no se detectó suficiente señal de generación AI.
- `REAL`: no se detectó suficiente señal deepfake.
- `AI`: generación sintética detectada.
- `DEEPFAKE`: manipulación detectada.
- `INCONCLUSIVE`: evidencia insuficiente.

`REAL` o `HUMAN` no prueban procedencia ni identidad. Confirmar suplantación exige una referencia facial/vocal consentida.

Consulte `calibration/README.md` para obtener métricas reproducibles.
