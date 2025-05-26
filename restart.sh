#!/bin/bash

echo "Stopping any running instances..."
pkill -f "uvicorn app.main:app" || true

echo "Starting MCP Sonarr server..."
cd /root/mcp-sonarr
source venv/bin/activate || python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload