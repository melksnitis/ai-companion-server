#!/bin/bash

# Set PATH to include npm global bin directory
export PATH="$PATH:$(npm config get prefix)/bin"

# Start the FastAPI server
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
