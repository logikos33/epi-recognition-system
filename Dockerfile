# Dockerfile for Render - EPI Recognition Worker (OPTIMIZED)
FROM python:3.11-slim

# Set environment variables for pip optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Set working directory
WORKDIR /opt/render/project/src

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy worker requirements (minimal - faster install)
COPY requirements-worker.txt .

# Install Python dependencies (with optimizations)
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-worker.txt && \
    rm -rf /root/.cache/pip

# Pre-download YOLO model ONLY (faster than full import)
RUN python -c "import requests; requests.get('https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt', stream=True).raise_for_status(); open('yolov8n.pt', 'wb').write(requests.get('https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt', stream=True).content); print('Model downloaded')"

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p storage/images storage/annotated storage/reports models

# Verify model is present
RUN ls -lh yolov8n.pt || echo "Model not found"

# Start command
CMD ["python", "cloud_worker.py"]
