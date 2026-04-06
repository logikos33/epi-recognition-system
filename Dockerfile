# EPI Monitor V2 — minimal Dockerfile for Railway
FROM python:3.11-slim

WORKDIR /app

# Install Python deps (psycopg2-binary includes libpq — no apt needed)
COPY requirements-railway.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-railway.txt

# Copy application code
COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["sh", "start.sh"]
