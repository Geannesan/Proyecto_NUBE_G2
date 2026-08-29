# DeepFakeShield

Plataforma web para analizar contenido sintético o manipulado en imágenes, audio y video.

## Resultado del análisis

El modo recomendado es **Análisis integral**. Mantiene tres ejes distintos:

- `generation`: contenido generado por IA (`AI` frente a `HUMAN`).
- `manipulation`: deepfake/manipulación (`DEEPFAKE` frente a `REAL`).
- `identity_impersonation`: requiere una referencia biométrica autorizada; sin ella devuelve `not_assessed`.

La confianza es la salida del modelo, no la precisión medida. La respuesta incluye calidad, SHA-256, validación C2PA, modelo y métricas cuando existe un dataset etiquetado.

## Ejecución local con Docker

```powershell
docker compose up --build
```

- Frontend: <http://localhost:8080>
- API: <http://localhost:8000>
- OpenAPI: <http://localhost:8000/docs>

Compose levanta frontend Nginx, API FastAPI y PostgreSQL, con volúmenes persistentes.

## Validación científica

Prepare un CSV siguiendo `Backend/calibration/predictions.example.csv`:

```powershell
cd Backend
python -m app.scripts.evaluate_predictions calibration/predictions.csv --output calibration/metrics.json
```

El dashboard cargará accuracy, precision, recall, F1, ROC-AUC, EER, Brier, FPR/FNR y calibración por medio y eje. El ejemplo no representa rendimiento real.

## Pruebas

```powershell
cd Backend
python -m pytest -q

cd ../Frontend
npm run lint
npm run build
```

Kubernetes se implementará después de validar esta arquitectura con datos etiquetados.
