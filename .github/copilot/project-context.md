# AI3 Project Context

## Project Overview

This is an NLP/AI pipeline using GPU acceleration with CUDA. The system consists of a Flask-based backend, a React frontend, and utilizes NVIDIA GPUs for model inference and training.

## Tech Stack

- **Backend**: Python Flask with SQLAlchemy
- **Frontend**: React with Vite
- **Database**: SQL database (managed through Alembic)
- **ML Infrastructure**: PyTorch, transformers, FAISS for vector indexing
- **Deployment**: Docker with NVIDIA CUDA support
- **CI/CD**: Drone CI with GPU testing capability

## Code Style Guidelines

- Python code follows PEP 8 guidelines
- Use type hints in Python functions
- Document public APIs with docstrings
- Organize code in modules and classes with single responsibility
- Write unit and integration tests for new features
- Use async processing for long-running operations

## Architecture Patterns

- Backend uses blueprint-based API organization
- Services layer abstracts business logic
- Models represent database entities
- Distributed indexing with FAISS
- Queue-based processing for file operations
