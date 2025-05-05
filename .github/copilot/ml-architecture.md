# ML Architecture Reference

## Model Versions

The system supports multiple model versions (v1, v2) with corresponding FAISS indexes.

## Embedding Models

- We use transformer-based models for generating embeddings
- Model parameters are configured through the embedding service
- All models require CUDA support for efficient inference

## Index Structure

- FAISS indexes are organized by version
- Distributed indexing splits workload across processing nodes
- Index health is monitored by a dedicated service

## Version Migration

- Migrations between model versions follow a structured process
- The index_version_manager handles version transitions
- Data consistency is maintained during migrations

## Processing Pipeline

1. Files are uploaded through the API
2. The queue service adds processing tasks to the queue
3. File processor consumers handle embedding generation
4. The distributed indexer adds embeddings to FAISS
5. The search API enables vector similarity search
