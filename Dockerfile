# EPI Monitor - Dockerfile para Railway
FROM python:3.11-slim

# Cache bust - force Railway to rebuild fresh (2026-04-01 15:10)
ARG CACHE_BUST=20260401-2203

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (force cache miss with CACHE_BUST)
ARG CACHE_BUST
COPY requirements.txt .

# Install Python dependencies (force cache miss with CACHE_BUST)
ARG CACHE_BUST
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Run the application with verification
CMD ["python", "railway_start.py"]
