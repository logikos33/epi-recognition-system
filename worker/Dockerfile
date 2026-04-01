# EPI Monitor V2 — Worker Service
# Imagem base com torch pré-instalado em camada separada
# Builds após primeira vez: ~3 minutos (só código)

FROM python:3.11-slim

# Instalar FFmpeg e dependências (camada cacheada)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Instalar torch PRIMEIRO em camada separada (~800MB)
# Só rebuilda se esta linha mudar — raro!
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
    torchvision --index-url https://download.pytorch.org/whl/cpu

# Instalar demais dependências Worker
COPY requirements.worker.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.worker.txt

# Copiar código
WORKDIR /app
COPY . .

# Diretórios
RUN mkdir -p storage/streams storage/models/active logs

# Health check Redis
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import redis,os; redis.from_url(os.environ.get('REDIS_URL','redis://localhost')).ping()" || exit 1

ENV SERVICE_TYPE=worker
CMD ["python3", "railway_start.py"]
