# Despliegue de DeepFakeShield

La plataforma se distribuye en tres servicios: frontend Nginx, API FastAPI y PostgreSQL. Los modelos se descargan desde Hugging Face la primera vez y se conservan en el PVC `huggingface-cache`.

## Docker Compose

1. Copiar `.env.example` como `.env` y cambiar `POSTGRES_PASSWORD`.
2. Construir y arrancar:

```powershell
docker compose build
docker compose up -d
docker compose ps
```

3. Abrir `http://localhost:8080`. La API queda disponible en `http://localhost:8000/docs`.

Para revisar fallos:

```powershell
docker compose logs -f backend
```

## Kubernetes local (Docker Desktop)

Los manifiestos usan el namespace `deepfakeshield`, Ingress Nginx y el host `deepfakeshield.local`.

1. Construir las imágenes locales:

```powershell
docker build -t deepfakeshield-backend:latest ./Backend
docker build -t deepfakeshield-frontend:latest ./Frontend
```

2. Cambiar la contraseña de `Kubernetes/secret.local.yaml` y mantener sincronizado el valor dentro de `DATABASE_URL`.
3. Aplicar y esperar:

```powershell
kubectl apply -k Kubernetes
kubectl rollout status statefulset/postgres -n deepfakeshield --timeout=180s
kubectl rollout status deployment/backend -n deepfakeshield --timeout=900s
kubectl rollout status deployment/frontend -n deepfakeshield --timeout=180s
kubectl get all,ingress,pvc -n deepfakeshield
```

4. Si no hay controlador Ingress, usar acceso inmediato por port-forward:

```powershell
kubectl port-forward service/frontend 8080:80 -n deepfakeshield
```

La aplicación estará en `http://localhost:8080`; Nginx del frontend enviará `/api` al servicio `backend`.

## Registro e infraestructura cloud

Antes de desplegar en un clúster remoto:

1. Publicar ambas imágenes en el registro elegido.
2. Sustituir los nombres mediante Kustomize:

```powershell
kubectl kustomize edit set image deepfakeshield-backend:latest=REGISTRY/deepfakeshield-backend:VERSION
kubectl kustomize edit set image deepfakeshield-frontend:latest=REGISTRY/deepfakeshield-frontend:VERSION
```

Ejecutar ese comando dentro de `Kubernetes` o editar la sección `images` de `kustomization.yaml`.

3. Configurar `CORS_ORIGINS` y el host del Ingress con el dominio real.
4. Crear el secreto directamente en el proveedor o con `kubectl create secret`; nunca publicar `secret.local.yaml`.
5. Añadir TLS con cert-manager o el gestor de certificados del proveedor.

## Recursos mínimos recomendados

- Backend CPU: 1 CPU / 2 GiB solicitados; límite 4 CPU / 8 GiB.
- Caché de modelos: PVC de 20 GiB.
- PostgreSQL: PVC de 10 GiB.
- Frontend: 2 réplicas de 64–256 MiB.

El backend queda en una réplica y estrategia `Recreate` porque comparte un PVC `ReadWriteOnce` para los modelos. Para escalar horizontalmente en cloud debe utilizar almacenamiento `ReadWriteMany`, caché precargada por nodo o incluir los checkpoints en una imagen/versionado de artefactos.

## Comprobaciones

```powershell
curl http://localhost:8080/health
kubectl logs deployment/backend -n deepfakeshield
kubectl describe pod -l app=backend -n deepfakeshield
```

La primera inferencia puede tardar mientras descarga el checkpoint. Para entornos sin Internet, precargar el PVC y cambiar `HF_LOCAL_ONLY=true`.

La imagen del backend instala PyTorch CPU para evitar dependencias CUDA innecesarias. Si el clúster dispone de GPU NVIDIA, cree una variante del Dockerfile con las ruedas CUDA, instale el NVIDIA Device Plugin, solicite `nvidia.com/gpu` y cambie `USE_CUDA=true`.
