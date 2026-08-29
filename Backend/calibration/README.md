# Validación de detectores

Esta carpeta separa la evaluación científica de la confianza mostrada por cada modelo.

1. Prepare un CSV con `media_type,axis,ground_truth,score`.
2. Use personas y fuentes distintas entre entrenamiento, validación y prueba.
3. Incluya originales, compresión web, múltiples generadores, replay y mala calidad.
4. Ejecute desde `Backend`:

```powershell
python -m app.scripts.evaluate_predictions calibration/predictions.csv --output calibration/metrics.json
```

`ground_truth=1` significa generado/manipulado; `0` significa auténtico. `score` es la probabilidad sospechosa entre 0 y 100. No publique resultados obtenidos con `predictions.example.csv`: solo prueba el formato.
