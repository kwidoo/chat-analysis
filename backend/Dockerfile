FROM rapidsai/base:24.10-cuda12.5-py3.11

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    libgomp1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Use python3 instead of python
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

# Copy requirements first
COPY install.sh .

# Install Python dependencies
RUN ./install.sh

# Create necessary directories
RUN mkdir -p /app/models/versions/v1 \
    /app/models/versions/v2 \
    /app/faiss/indexes/model_v1 \
    /app/faiss/indexes/model_v2 \
    /app/queues \
    /app/db

# Copy application code
COPY . .

# Add database migration script
COPY ./scripts/db_migrate.sh /app/scripts/
RUN chmod +x /app/scripts/db_migrate.sh

# Validate CUDA availability
RUN python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device count:', torch.cuda.device_count())"

# Healthcheck
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Set active model
ENV ACTIVE_MODEL=v1

# Run database migrations and the application with gunicorn
ENTRYPOINT ["/app/scripts/db_migrate.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
