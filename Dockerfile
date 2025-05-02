FROM python:3.8-slim

# Setup for Apple M1 GPU support
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/homebrew/bin:${PATH}"

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .

CMD ["python", "app.py"]
