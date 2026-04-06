# EPI Monitor V2 — diagnostic minimal
FROM python:3.11-slim

WORKDIR /app

COPY requirements-railway.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-railway.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Use shell form so $PORT is expanded
CMD gunicorn minimal_wsgi:app --workers 1 --timeout 60 --bind 0.0.0.0:${PORT:-8080} --log-level info
