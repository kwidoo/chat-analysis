## ✅ Audit & Fix: SQLAlchemy + Alembic + DB CLI Configuration

### ✅ Tasks

- [x] **Fix SQLAlchemy model compatibility**

  - [x] In `models/user.py`: rename `metadata` field → `metadata_json` to avoid `InvalidRequestError: Attribute name 'metadata' is reserved`.
  - [x] Ensure all models use `db.Model` and avoid conflicts with reserved SQLAlchemy names.

- [x] **Standardize imports and package structure**

  - [x] Replace `from app.models.user import Role` → `from models.user import Role` in CLI and service code.
  - [x] Replace `from app import app` with Flask's `current_app` or refactor to use `create_app()` with `app_context()` in CLI logic.
  - [x] Ensure `backend/` is a Python package (`__init__.py`) and `PYTHONPATH` includes `/app` inside Docker.

- [x] **Update Alembic configuration**

  - [x] Set `sqlalchemy.url` dynamically using app config instead of hardcoded SQLite path in `alembic.ini`.
  - [x] Move DB URL resolution to `env.py` inside Alembic migrations folder using `from core.config import get_db_url()` or similar helper.

- [x] **Test and stabilize CLI commands**

  - [x] Validate all `flask db_commands` (init, upgrade, migrate, create-roles, create-admin) work inside Docker using:
    ```bash
    docker-compose exec backend flask db_commands upgrade
    docker-compose exec backend flask db_commands create-roles
    ```
  - [x] Add unit tests (optional) to validate CLI command behavior with test DB.

- [x] **Update Docker config for Alembic + Flask CLI**

  - [x] Ensure `FLASK_APP=app.py` is set in `docker-compose.yml` environment.
  - [x] Mount Alembic's `migrations/` directory properly into container.

- [x] **Add `.env` and `.flaskenv` consistency**
  - [x] Ensure `.env` includes correct `DB_TYPE`, `DB_PATH`, `DB_HOST`, etc.
  - [x] Optionally add `.flaskenv` with:
    ```
    FLASK_APP=app.py
    FLASK_ENV=development
    ```
