#!/bin/bash

# Exit on error
set -e

# Handle process termination
trap "exit" TERM

# Run database migrations
uv run alembic upgrade head &

# Start FastAPI server
uv run uvicorn app.app:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=* &

# Start mkdocs documentation server
uv run mkdocs serve -a 0.0.0.0:8080 &

# Wait for all background processes
wait
