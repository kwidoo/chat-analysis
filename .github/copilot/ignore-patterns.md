# Copilot Ignore Patterns

The following patterns specify files and directories that should be ignored by GitHub Copilot when generating suggestions:

- `**/node_modules/**`
- `**/__pycache__/**`
- `**/.git/**`
- `**/venv/**`
- `**/dist/**`
- `**/build/**`
- `**/migrations/versions/**` (except for schema definitions)
- `**/uploads/**`
- `**/flask_session/**`
- `**/flask_sessions/**`
- `**/faiss/indexes/**` (large binary files)
- `**/queues/processing_queue.pkl`
