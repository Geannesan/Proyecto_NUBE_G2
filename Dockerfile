# Usar una imagen ligera de Python
FROM python:3.11-slim

# Configurar el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de requerimientos primero (para aprovechar la caché de Docker)
COPY requirements.txt .

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del Backend al contenedor
COPY ./Backend ./Backend

# Exponer el puerto en el que corre Uvicorn
EXPOSE 8000

# Comando para arrancar la aplicación
CMD ["uvicorn", "Backend.main:app", "--host", "0.0.0.0", "--port", "8000"]