FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente y artefactos entrenados
COPY . .

# Puerto expuesto por defecto
EXPOSE 8001
ENV PORT=8001

# Ejecutar servidor FastAPI con Uvicorn
CMD ["sh", "-c", "uvicorn servidor_api_nlp:app --host 0.0.0.0 --port ${PORT:-8001}"]
