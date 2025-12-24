# AI Companion Server - Debugging Guide

This guide helps you manually test and debug the AI Companion Server components to understand if services are working correctly.

## Architecture Overview

```
User Request → FastAPI (port 8000) → Claude Agent SDK → Claude Code Router (port 3000) → OpenRouter → DeepSeek
```

## Prerequisites

- Docker container running: `docker ps | grep ai-companion-server`
- Services should be accessible on ports 8000 (FastAPI) and 3000 (Router)

---

## Step 1: Verify Container is Running

```bash
# Check container status
docker ps | grep ai-companion-server

# Check container logs
docker-compose logs ai-companion --tail=50

# Access container shell
docker exec -it ai-companion-server bash
```

**Expected:** Container should be running and healthy.

---

## Step 2: Check Environment Variables

```bash
# Check if OpenRouter API key is loaded
docker exec ai-companion-server bash -c 'echo "OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:0:20}..."'
docker exec ai-companion-server bash -c 'echo "Key length: ${#OPENROUTER_API_KEY}"'

# Check all relevant env vars
docker exec ai-companion-server printenv | grep -E "OPENROUTER|ANTHROPIC|LETTA"
```

**Expected:**
- `OPENROUTER_API_KEY` should be 73 characters (starts with `sk-or-v1-`)
- `ANTHROPIC_API_KEY` may be empty (we use OpenRouter key instead)
- `LETTA_API_KEY` should be set if using Letta

---

## Step 3: Test FastAPI Health Endpoint

```bash
# Test health endpoint
curl -s http://localhost:8000/health | jq '.'
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

---

## Step 4: Check Claude Code Router Status

```bash
# Check router status
docker exec ai-companion-server ccr status

# Check router health endpoint
curl -s http://localhost:3000/health | jq '.'
```

**Expected:**
- Router should show "Status: Running" on port 3000
- Health endpoint should return: `{"status":"ok","timestamp":"..."}`

**If router is not running:**
```bash
# Start the router
docker exec ai-companion-server ccr start

# Wait a few seconds and check status again
sleep 3
docker exec ai-companion-server ccr status
```

---

## Step 5: Verify Router Configuration

```bash
# Check router config
docker exec ai-companion-server cat /root/.claude-code-router/config.json | jq '.'

# Check if API key is set (should NOT be ${OPENROUTER_API_KEY} placeholder)
docker exec ai-companion-server cat /root/.claude-code-router/config.json | jq '.Providers[0].api_key'
```

**Expected:**
- `api_key` should be the actual key value (starts with `sk-or-v1-`), NOT `${OPENROUTER_API_KEY}`
- `PORT` should be `3000`
- `Providers[0].name` should be `"openrouter"`
- `Providers[0].models` should include `"deepseek/deepseek-chat"`

**If API key is still a placeholder:**
```bash
# Update config with actual key
OPENROUTER_KEY=$(docker exec ai-companion-server printenv OPENROUTER_API_KEY)
cat > /tmp/router-config.json << EOF
{
  "APIKEY": "your-router-secret-key",
  "HOST": "0.0.0.0",
  "PORT": 3000,
  "LOG": true,
  "LOG_LEVEL": "info",
  "API_TIMEOUT_MS": 600000,
  "NON_INTERACTIVE_MODE": true,
  "Providers": [
    {
      "name": "openrouter",
      "api_base_url": "https://openrouter.ai/api/v1/chat/completions",
      "api_key": "$OPENROUTER_KEY",
      "models": ["deepseek/deepseek-chat"],
      "transformer": {
        "use": ["openrouter", "deepseek", "tool_use"]
      }
    }
  ],
  "Router": {
    "default": "openrouter,deepseek/deepseek-chat",
    "background": "openrouter,deepseek/deepseek-chat",
    "think": "openrouter,deepseek/deepseek-chat",
    "longContext": "openrouter,deepseek/deepseek-chat",
    "longContextThreshold": 60000
  }
}
EOF

# Copy to container and restart router
docker exec ai-companion-server ccr stop
docker cp /tmp/router-config.json ai-companion-server:/root/.claude-code-router/config.json
docker exec ai-companion-server ccr start
sleep 3
```

---

## Step 6: Test Router Directly with OpenRouter

```bash
# Get the API key from container
OPENROUTER_KEY=$(docker exec ai-companion-server printenv OPENROUTER_API_KEY)

# Test router with a simple message
curl -s http://localhost:3000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $OPENROUTER_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "deepseek/deepseek-chat",
    "max_tokens": 50,
    "messages": [{"role": "user", "content": "What is 2+2? Answer briefly."}]
  }' | jq '.'
```

**Expected Response:**
```json
{
  "id": "...",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "2 + 2 = 4"
    }
  ],
  ...
}
```

**Common Errors:**
- `"Invalid API key"` - Router config still has placeholder, not actual key
- Connection timeout - Router not running or wrong port
- `404 Not Found` - Wrong endpoint URL

---

## Step 7: Test OpenRouter Directly (Bypass Router)

```bash
# Test OpenRouter API directly
OPENROUTER_KEY=$(docker exec ai-companion-server printenv OPENROUTER_API_KEY)

curl -s https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_KEY" \
  -d '{
    "model": "deepseek/deepseek-chat",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "max_tokens": 50
  }' | jq '.choices[0].message.content'
```

**Expected:** Should return the answer (e.g., "2 + 2 = 4")

**If this fails:** Your OpenRouter API key is invalid or has no credits.

---

## Step 8: Test Claude Agent SDK Configuration

```bash
# Check if ANTHROPIC_BASE_URL is set correctly in AgentService
docker exec ai-companion-server python -c "
import os
from app.config import settings
from app.services.agent_service import AgentService

service = AgentService()
print('ANTHROPIC_API_KEY set:', 'Yes' if os.getenv('ANTHROPIC_API_KEY') else 'No')
print('ANTHROPIC_API_KEY length:', len(os.getenv('ANTHROPIC_API_KEY', '')))
print('ANTHROPIC_BASE_URL:', os.getenv('ANTHROPIC_BASE_URL', 'Not set'))
"
```

**Expected:**
- `ANTHROPIC_API_KEY set: Yes`
- `ANTHROPIC_API_KEY length: 73`
- `ANTHROPIC_BASE_URL: http://localhost:3000`

---

## Step 9: Test FastAPI Chat Endpoint

```bash
# Test streaming chat endpoint
curl -s -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2? Answer in one sentence.", "conversation_id": "test-debug"}' \
  2>&1 | head -50
```

**Expected Response (SSE format):**
```
data: {"event": "conversation_id", "data": {"id": "test-debug"}}

data: {"event": "thinking_start", "data": {"message": "Thinking..."}}

data: {"event": "thinking_stop", "data": {}}

data: {"event": "message_start", "data": {"agent_id": "test-debug", "note": "Model selected by Claude Code Router"}}

data: {"event": "content_delta", "data": {"text": "2 + 2 equals 4."}}

data: {"event": "message_stop", "data": {"stop_reason": "end_turn"}}

data: {"event": "done", "data": {}}
```

**Common Issues:**
- Request times out after `message_start` - Router not responding (check Step 6)
- `Internal Server Error` - Check FastAPI logs: `docker-compose logs ai-companion --tail=50`
- No `content_delta` events - Claude Agent SDK not connecting to router

---

## Step 10: Check FastAPI Logs for Errors

```bash
# View recent logs
docker-compose logs ai-companion --tail=100

# Follow logs in real-time
docker-compose logs -f ai-companion

# Search for errors
docker-compose logs ai-companion | grep -i "error\|traceback\|exception"
```

---

## Step 11: Test Available Tools Endpoint

```bash
# List available tools
curl -s http://localhost:8000/tools/ | jq '.'
```

**Expected:** Should return list of Claude Agent SDK tools (Bash, Read, Write, Edit, Glob, Search)

---

## Step 12: Run Integration Tests

```bash
# Make test scripts executable
chmod +x tests/integration/*.sh

# Run chat tests
./tests/integration/test-chat.sh

# Run router tests
./tests/integration/test-router.sh
```

---

## Common Issues and Solutions

### Issue: Router returns "Invalid API key"

**Cause:** Router config has `${OPENROUTER_API_KEY}` placeholder instead of actual key.

**Solution:** Follow Step 5 to update router config with actual key value.

---

### Issue: Chat request times out after `message_start`

**Cause:** Claude Agent SDK can't communicate with router or router can't reach OpenRouter.

**Debug:**
1. Test router directly (Step 6) - if this fails, router config is wrong
2. Test OpenRouter directly (Step 7) - if this fails, API key is invalid
3. Check Claude Agent SDK env vars (Step 8) - ensure `ANTHROPIC_BASE_URL` is set

---

### Issue: `ANTHROPIC_BASE_URL` not set

**Cause:** AgentService `__init__` not being called or environment not persisting.

**Solution:** Verify in `app/services/agent_service.py`:
```python
def __init__(self):
    os.environ["ANTHROPIC_API_KEY"] = settings.openrouter_api_key or settings.anthropic_api_key
    os.environ["ANTHROPIC_BASE_URL"] = "http://localhost:3000"
```

---

### Issue: Router not starting automatically

**Cause:** Startup script not running or failing.

**Solution:**
```bash
# Manually start router
docker exec ai-companion-server ccr start

# Check startup script
docker exec ai-companion-server cat /app/scripts/start-services.sh
```

---

## Quick Diagnostic Checklist

Run these commands in sequence to quickly identify issues:

```bash
# 1. Container running?
docker ps | grep ai-companion-server

# 2. FastAPI healthy?
curl -s http://localhost:8000/health

# 3. Router running?
docker exec ai-companion-server ccr status

# 4. Router healthy?
curl -s http://localhost:3000/health

# 5. API key loaded?
docker exec ai-companion-server bash -c 'echo ${#OPENROUTER_API_KEY}'

# 6. Router config correct?
docker exec ai-companion-server cat /root/.claude-code-router/config.json | grep -A 1 '"api_key"'

# 7. Test router directly
OPENROUTER_KEY=$(docker exec ai-companion-server printenv OPENROUTER_API_KEY)
curl -s http://localhost:3000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $OPENROUTER_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"deepseek/deepseek-chat","max_tokens":20,"messages":[{"role":"user","content":"Hi"}]}'

# 8. Test chat endpoint
curl -s -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Hi","conversation_id":"test"}' | head -20
```

---

## Getting Help

If you're still stuck after following this guide:

1. **Collect diagnostic info:**
   ```bash
   # Save all diagnostic output
   ./tests/integration/test-chat.sh > debug-output.txt 2>&1
   docker-compose logs ai-companion >> debug-output.txt
   docker exec ai-companion-server ccr status >> debug-output.txt
   ```

2. **Check the logs** for specific error messages
3. **Review the architecture** - ensure you understand the request flow
4. **Test each component individually** - isolate where the failure occurs

---

## Success Criteria

All tests pass when:
- ✅ FastAPI health endpoint returns `200 OK`
- ✅ Router status shows "Running" on port 3000
- ✅ Router health endpoint returns `{"status":"ok"}`
- ✅ Router config has actual API key (not placeholder)
- ✅ Direct router test returns valid response from DeepSeek
- ✅ Chat endpoint returns content_delta events with actual text
- ✅ Integration tests pass (7/7 for chat, all for router)
