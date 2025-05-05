from logging.config import fileConfig
import os
import sys
from alembic import context
from sqlalchemy import engine_from_config, pool

# This adds the parent directory to the Python path so we can import our app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import Base
import models.user  # Import models to ensure they're registered with SQLAlchemy

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Set the SQLAlchemy URL from environment if available
section = config.config_ini_section
db_url = os.environ.get("DATABASE_URL")
if db_url:
    config.set_section_option(section, "sqlalchemy.url", db_url)

# Set target metadata
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
    url = config.get_section_option(config.config_ini_section, "sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


# Execute migration function based on mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
