#!/bin/bash
set -e

# Wait for potential database to be ready (especially important if using MySQL)
if [ "$DB_TYPE" = "mysql" ]; then
    echo "Waiting for database to be ready..."
    MAX_RETRIES=30
    RETRY_INTERVAL=2
    retries=0

    while [ $retries -lt $MAX_RETRIES ]; do
        if nc -z -w1 $DB_HOST $DB_PORT; then
            echo "Database is ready!"
            break
        fi
        echo "Waiting for database connection... ($((retries+1))/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
        retries=$((retries+1))
    done

    if [ $retries -eq $MAX_RETRIES ]; then
        echo "Could not connect to the database after $MAX_RETRIES attempts"
        exit 1
    fi
fi

# Run database migrations
echo "Running database migrations..."
cd /app
flask db upgrade || (echo "Migration command failed. Will try to create tables directly."; FLASK_APP=app.py python -c "from app import app; app.app_context().push(); from db.session import db; db.create_all()")

echo "Migrations completed successfully"

# Execute the CMD
echo "Starting application..."
exec "$@"
