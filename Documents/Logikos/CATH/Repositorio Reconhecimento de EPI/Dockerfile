# Railway Deployment - Force Nixpacks-style build
# This Dockerfile replicates the Nixpacks.toml configuration

FROM python:3.11-slim

# Install system dependencies
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

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create virtual environment for PEP 668 compliance
RUN python3.11 -m venv /opt/venv

# Install from requirements-railway.txt into venv
RUN . /opt/venv/bin/activate && \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements-railway.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Start application with gunicorn
CMD ["/opt/venv/bin/gunicorn", "api_server:app", "--worker-class", "eventlet", "--worker-connections", "1000", "--timeout", "120", "--bind", "0.0.0.0:$PORT"]
# CACHE BUST - 1775422685 - Force Railway fresh build
# CACHE BUST - 1775425367 - Force Railway fresh build
