# Minimal Dockerfile for Railway - EPI Recognition API
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV (Debian Trixie compatible)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first (for better caching)
COPY requirements-api.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-api.txt

# Copy application code
COPY api_server.py .

# Create models directory
RUN mkdir -p models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5001

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/health')" || exit 1

# Start the application
CMD ["python", "api_server.py"]
