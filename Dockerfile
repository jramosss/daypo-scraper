# Usar la imagen oficial de Python como base
FROM python:3.11-slim

# Evitar que Python genere archivos .pyc y habilitar el logeo inmediato
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias mínimas del sistema para poder ejecutar la instalación de Playwright
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar los navegadores de Playwright y SUS dependencias de sistema automáticamente
RUN playwright install chromium
RUN playwright install-deps chromium

# Copiar el resto del código del proyecto
COPY . .

# Exponer el puerto de la API
EXPOSE 8005

# Comando para ejecutar la API de FastAPI
CMD ["python", "api.py"]
