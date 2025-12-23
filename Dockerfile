FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code Router globally
RUN npm install -g @anthropic-ai/claude-code @musistudio/claude-code-router

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy router configuration
COPY router/config.json /root/.claude-code-router/config.json

# Create necessary directories
RUN mkdir -p /app/workspace /app/data /root/.claude-code-router/logs

# Copy startup script
COPY scripts/start-services.sh /app/start-services.sh
RUN chmod +x /app/start-services.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose ports (8000 for FastAPI, 3000 for router)
EXPOSE 8000 3000

# Run both services
CMD ["/app/start-services.sh"]
