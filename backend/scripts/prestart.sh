#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Setup database roles for RLS (if enabled)
if [ "${RLS_ENABLED:-true}" = "true" ]; then
    echo "Setting up RLS database roles..."
    python scripts/setup_db_roles.py
else
    echo "RLS disabled, skipping database role setup"
fi

# Run migrations (includes RLS policy setup)
echo "Running database migrations..."
alembic upgrade head

# Create initial data in DB
echo "Creating initial data..."
python app/initial_data.py

echo "✅ Backend startup completed successfully"
