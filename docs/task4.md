This is new docker-compose.yaml version, could you add it and adjust other files if required. Also make nodejs version 22+

version: "3.8"

services:
backend:
build: .
ports: - "5000:5000"
volumes: - ./backend/models:/app/models - ./backend/faiss:/app/faiss - ./backend/queues:/app/queues
networks: - analysis-net
depends_on: - dask-scheduler
environment: - ACTIVE_MODEL=v1 - PYTHONUNBUFFERED=1

frontend:
build: ./frontend
ports: - "3000:3000"
depends_on: - backend
networks: - analysis-net

dask-scheduler:
image: daskdev/dask:latest
command: dask-scheduler
ports: - "8786:8786" - "8787:8787"
networks: - analysis-net

dask-worker:
image: daskdev/dask:latest
command: dask-worker dask-scheduler:8786
deploy:
replicas: 2
networks: - analysis-net

networks:
analysis-net:
driver: bridge
