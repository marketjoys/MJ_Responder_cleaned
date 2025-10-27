#!/bin/bash

# Start Backend Server on Port 9000
# This script starts the FastAPI backend server

cd /app/backend

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start uvicorn server
echo "🚀 Starting Email Automation Backend on port 9000..."
uvicorn server:app --host 0.0.0.0 --port 9000 --reload

# For production without reload:
# uvicorn server:app --host 0.0.0.0 --port 9000 --workers 4
