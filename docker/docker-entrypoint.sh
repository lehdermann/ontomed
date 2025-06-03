#!/bin/sh

# Wait for database to be ready
until nc -z -v -w30 db 5432
    do
        echo "Waiting for database connection..."
        sleep 1
    done

echo "Database is ready"

# Start the application
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
