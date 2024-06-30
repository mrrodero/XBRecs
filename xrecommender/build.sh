#!/usr/bin/env bash

set -o errexit  # exit on error

# Log file path (adjust as needed)
LOG_FILE="build.log"

echo "=== Starting build process ==="

# Install Python dependencies
echo "--- Installing Python dependencies ---"
pip3 install -r requirements.txt >> "$LOG_FILE"  # Redirect output to log file

# Rebuild Whoosh index
echo "--- Rebuilding Whoosh index ---"
python manage.py rebuild_index --noinput >> "$LOG_FILE"

# Collect static files
echo "--- Collecting static files ---"
python3 manage.py collectstatic --no-input >> "$LOG_FILE"

echo "=== Build process completed ==="
