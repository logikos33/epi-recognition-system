# Dockerfile for Render - EPI Recognition Worker
FROM python:3.11-slim

# Set working directory
WORKDIR /opt/render/project/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download YOLO model to avoid first-run timeout
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt'); print('Model downloaded successfully')"

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p storage/images storage/annotated storage/reports models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Start command
CMD ["python", "cloud_worker.py"]
