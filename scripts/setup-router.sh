#!/bin/bash
set -e

echo "🚀 Setting up Claude Code Router..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check required environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY is not set"
    echo "Please set it in .env file or export it"
    exit 1
fi

echo "✅ Docker is running"
echo "✅ Environment variables are set"

# Build and start services
echo ""
echo "📦 Building Docker images..."
docker-compose build ai-companion

echo ""
echo "🚀 Starting services..."
docker-compose up -d ai-companion ollama

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check service health
echo ""
echo "🔍 Checking service health..."

if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ AI Companion Server is healthy"
else
    echo "⚠️  AI Companion Server is not responding yet"
fi

if curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo "✅ Claude Code Router is healthy"
else
    echo "⚠️  Claude Code Router is not responding yet"
fi

if curl -f http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "✅ Ollama is healthy"
else
    echo "⚠️  Ollama is not responding yet"
fi

echo ""
echo "📋 Service URLs:"
echo "  - AI Companion Server: http://localhost:8000"
echo "  - Claude Code Router:  http://localhost:3000"
echo "  - Ollama:              http://localhost:11434"

echo ""
echo "🎯 Next steps:"
echo "  1. Install Claude Code Router CLI:"
echo "     npm install -g @musistudio/claude-code-router"
echo ""
echo "  2. Activate the router:"
echo "     ccr activate http://localhost:3000 ${ROUTER_API_KEY:-your-router-secret-key}"
echo ""
echo "  3. Start Claude Code:"
echo "     ccr code"
echo ""
echo "  4. Switch models with /model command"
echo ""
echo "📚 See router/README.md for more details"
