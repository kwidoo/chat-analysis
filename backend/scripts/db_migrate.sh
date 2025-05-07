#!/bin/bash
set -e

# Ensure Python can find backend modules
export PYTHONPATH=/app:$PYTHONPATH
export FLASK_APP="app:app"

# Wait for DB if needed
if [ "$DB_TYPE" = "mysql" ] || [ "$DB_TYPE" = "mariadb" ]; then
    echo "Waiting for database at $DB_HOST:$DB_PORT..."
    MAX_RETRIES=30
    RETRY_INTERVAL=2
    retries=0
    until nc -z -w1 "$DB_HOST" "$DB_PORT" || [ $retries -eq $MAX_RETRIES ]; do
        echo "  Retry $((retries+1))/$MAX_RETRIES: Waiting..."
        sleep $RETRY_INTERVAL
        retries=$((retries + 1))
    done

    if [ $retries -eq $MAX_RETRIES ]; then
        echo "❌ Failed to connect to database at $DB_HOST:$DB_PORT"
        exit 1
    fi

    echo "✅ Database is ready!"
fi

# Run migrations
echo "🚀 Running database migrations..."
flask db-commands upgrade || {
     echo "⚠️ Migration failed, attempting direct table creation..."
     flask db-commands init
}

# Start the app
echo "📦 Starting app..."
exec "$@"
