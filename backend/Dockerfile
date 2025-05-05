FROM python:3.10.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY install.sh .

# Install Python dependencies
RUN ./install.sh

# Create necessary directories
RUN mkdir -p /app/models/versions/v1 \
    /app/models/versions/v2 \
    /app/faiss/indexes/model_v1 \
    /app/faiss/indexes/model_v2 \
    /app/queues

# Copy application code
COPY . .

# Healthcheck
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Set active model
ENV ACTIVE_MODEL=v1

# Run the application with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
