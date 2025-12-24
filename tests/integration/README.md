# Integration Tests

Bash-based integration tests for the AI Companion Server and Claude Code Router.

## Prerequisites

- Docker and Docker Compose running
- `curl` installed
- `websocat` (optional, for WebSocket tests): `brew install websocat`
- Services running: `docker-compose up -d`

## Test Scripts

### 1. Chat & Streaming Tests (`test-chat.sh`)

Tests the FastAPI backend chat functionality including:
- ✅ Health check endpoint
- ✅ Root endpoint
- ✅ SSE streaming chat
- ✅ WebSocket connection
- ✅ Tools endpoint
- ✅ Memory endpoint
- ✅ Workspace endpoint

**Usage:**
```bash
# Run with default settings (localhost:8000)
./tests/integration/test-chat.sh

# Run with custom API URL
API_BASE_URL=http://192.168.1.100:8000 ./tests/integration/test-chat.sh
```

**Expected Output:**
```
🧪 AI Companion Server - Chat Integration Tests
================================================

Testing API at: http://localhost:8000

🔍 Checking if server is running...
✓ Server is healthy

📋 Test 1: Health Check
----------------------
✓ Health check passed

📋 Test 2: Root Endpoint
----------------------
✓ Root endpoint returned correct app name

📋 Test 3: Chat Streaming (SSE)
------------------------------
✓ Received SSE streaming events
✓ Received conversation_id event
✓ Received content streaming events
✓ Stream completed with done event

...

✓ All tests passed!
```

### 2. Router Tests (`test-router.sh`)

Tests the Claude Code Router integration including:
- ✅ Router health check
- ✅ Configuration validation
- ✅ Provider configuration (Anthropic, OpenRouter, Ollama, Local)
- ✅ Route configuration (default, background, think)
- ✅ Both services running in single container
- ✅ Router logs
- ✅ Environment variables

**Usage:**
```bash
# Run with default settings (localhost:3000)
./tests/integration/test-router.sh

# Run with custom router URL
ROUTER_URL=http://192.168.1.100:3000 ./tests/integration/test-router.sh
```

**Expected Output:**
```
🧪 Claude Code Router - Integration Tests
==========================================

Testing Router at: http://localhost:3000

🔍 Checking if Claude Code Router is running...
✓ Router is healthy

📋 Test 1: Router Health Check
-----------------------------
✓ Router health endpoint accessible

📋 Test 2: Router Configuration
------------------------------
✓ Router configuration file exists
✓ Router configuration is valid JSON

...

✓ All router tests passed!
```

## Running All Tests

```bash
# Start services
docker-compose up -d

# Wait for services to be ready
sleep 10

# Run all tests
./tests/integration/test-chat.sh && ./tests/integration/test-router.sh
```

## Troubleshooting

### Server Not Responding
```bash
# Check if containers are running
docker-compose ps

# Check logs
docker-compose logs ai-companion

# Restart services
docker-compose restart
```

### Tests Failing
```bash
# Check service health manually
curl http://localhost:8000/health
curl http://localhost:3000/health

# Check environment variables
docker exec ai-companion-server env | grep API_KEY

# View detailed logs
docker-compose logs -f ai-companion
```

### WebSocket Test Skipped
Install `websocat`:
```bash
# macOS
brew install websocat

# Linux
cargo install websocat

# Or skip WebSocket tests (they're optional)
```

## CI/CD Integration

These tests can be integrated into GitHub Actions or other CI/CD pipelines:

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: docker-compose up -d
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      
      - name: Wait for services
        run: sleep 15
      
      - name: Run chat tests
        run: ./tests/integration/test-chat.sh
      
      - name: Run router tests
        run: ./tests/integration/test-router.sh
```

## Test Coverage

### Current Coverage
- ✅ HTTP endpoints (health, root, tools, memory, workspace)
- ✅ SSE streaming
- ✅ WebSocket connections
- ✅ Router configuration
- ✅ Multi-service container
- ✅ Environment validation

### Future Tests
- ⏳ Actual AI chat responses (requires API keys)
- ⏳ Tool execution (Bash, Read, Write, Edit)
- ⏳ Memory persistence across conversations
- ⏳ Model routing and switching
- ⏳ Letta memory integration
- ⏳ Load testing
- ⏳ Error handling and edge cases

## Contributing

When adding new tests:
1. Follow the existing test structure
2. Use colored output for readability
3. Provide clear error messages
4. Make tests idempotent (can run multiple times)
5. Document any new dependencies
6. Update this README
