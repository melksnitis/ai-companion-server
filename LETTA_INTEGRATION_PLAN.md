# Option 1: Use Letta's LLM Provider Integration Plan

## Overview

Replace OpenRouter/DeepSeek integration with Letta's native LLM provider to achieve full memory persistence and learning capabilities through the Letta Learning SDK.

## Architecture Change

### Current Architecture (feature/letta-learning-sdk)
```
User → FastAPI → AgentService → learning() → Claude Agent SDK → OpenRouter → DeepSeek v3.2
                                    ↓
                              Letta Memory ✗ (fails: provider not supported)
```

### Target Architecture (Option 1)
```
User → FastAPI → AgentService → learning() → Claude Agent SDK → Letta Provider → Letta LLM
                                    ↓
                              Letta Memory ✓ (fully supported)
```

## Implementation Steps

### Phase 1: Configure Letta Provider

#### 1.1 Update Environment Configuration
**File:** `.env.example` and `.env`

```bash
# Remove OpenRouter configuration
# OPENROUTER_API_KEY=your-openrouter-key

# Keep Letta configuration
LETTA_API_KEY=your-letta-api-key
LETTA_BASE_URL=https://api.letta.com
LETTA_AGENT_NAME=evolving-assistant

# Remove Anthropic API configuration
# ANTHROPIC_API_KEY=
# ANTHROPIC_BASE_URL=
# ANTHROPIC_AUTH_TOKEN=
```

#### 1.2 Update Config Settings
**File:** `app/config.py`

```python
class Settings(BaseSettings):
    # Remove OpenRouter settings
    # openrouter_api_key: str = ""
    
    # Remove Anthropic settings
    # anthropic_api_key: str = ""
    
    # Keep Letta settings
    letta_api_key: str = ""
    letta_base_url: str = "https://api.letta.com"
    letta_agent_name: str = "evolving-assistant"
    
    # Add Letta LLM configuration
    letta_model: str = "gpt-4"  # Letta supports: gpt-4, gpt-3.5-turbo, claude-3-opus, etc.
    max_tokens: int = 4096
```

### Phase 2: Refactor AgentService

#### 2.1 Remove OpenRouter Configuration
**File:** `app/services/agent_service.py`

**Remove:**
```python
def __init__(self):
    # Remove OpenRouter configuration
    os.environ["ANTHROPIC_BASE_URL"] = "https://openrouter.ai/api"
    os.environ["ANTHROPIC_AUTH_TOKEN"] = settings.openrouter_api_key
    os.environ["ANTHROPIC_API_KEY"] = ""
```

**Replace with:**
```python
def __init__(self):
    # Configure Letta Learning SDK
    if settings.letta_api_key:
        os.environ["LETTA_API_KEY"] = settings.letta_api_key
    if settings.letta_base_url:
        os.environ["LETTA_BASE_URL"] = settings.letta_base_url
    
    self.agent_name = settings.letta_agent_name
    self.model = settings.letta_model
```

#### 2.2 Update Claude Agent SDK Configuration
**File:** `app/services/agent_service.py`

**Current:**
```python
def _get_agent_options(self) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        permission_mode="dontAsk",
        allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Search", "WebSearch"],
        model="deepseek/deepseek-v3.2",  # OpenRouter model
        cwd="/app/workspace",
    )
```

**Update to:**
```python
def _get_agent_options(self) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        permission_mode="dontAsk",
        allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Search"],
        model=self.model,  # Use Letta-configured model
        cwd="/app/workspace",
    )
```

**Note:** Remove `WebSearch` as it's only available on Anthropic's native API.

#### 2.3 Configure Letta Provider in Claude Agent SDK

The Claude Agent SDK needs to be configured to use Letta's API endpoint instead of Anthropic's:

```python
def __init__(self):
    # Configure Claude Agent SDK to use Letta's API
    os.environ["ANTHROPIC_BASE_URL"] = settings.letta_base_url
    os.environ["ANTHROPIC_API_KEY"] = settings.letta_api_key
    
    # Configure Letta Learning SDK
    if settings.letta_api_key:
        os.environ["LETTA_API_KEY"] = settings.letta_api_key
    
    self.agent_name = settings.letta_agent_name
    self.model = settings.letta_model
```

### Phase 3: Update Docker Configuration

#### 3.1 Update docker-compose.yml
**File:** `docker-compose.yml`

```yaml
services:
  ai-companion:
    environment:
      # Remove OpenRouter configuration
      # - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      
      # Remove Anthropic configuration
      # - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      
      # Keep Letta configuration
      - LETTA_API_KEY=${LETTA_API_KEY}
      - LETTA_BASE_URL=${LETTA_BASE_URL:-https://api.letta.com}
      - LETTA_AGENT_NAME=${LETTA_AGENT_NAME:-evolving-assistant}
      - LETTA_MODEL=${LETTA_MODEL:-gpt-4}
      - MAX_TOKENS=${MAX_TOKENS:-4096}
```

#### 3.2 Remove Claude Code Router
**File:** `docker-compose.yml` and `scripts/start-services.sh`

Since we're using Letta's provider, we no longer need the Claude Code Router:

```yaml
# Remove router volume mounts
volumes:
  - ./workspace:/app/workspace
  - ./data:/app/data
  # Remove: - ./router/config.json:/root/.claude-code-router/config.json
  # Remove: - router_logs:/root/.claude-code-router/logs
```

**File:** `scripts/start-services.sh`

```bash
#!/bin/bash
# Remove Claude Code Router startup
# echo "📡 Starting Claude Code Router on port 3000..."
# ccr start

echo "🐍 Starting FastAPI server on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Phase 4: Update Requirements

#### 4.1 Update requirements.txt
**File:** `requirements.txt`

```python
# Core Framework
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.18

# Letta Learning SDK with Claude Agent SDK
agentic-learning>=0.4.3
claude-agent-sdk>=0.1.0
# Remove: anthropic==0.42.0  # Not needed, using Letta's API

# WebSocket support
websockets==14.1

# Database & Storage
aiosqlite==0.20.0
sqlalchemy[asyncio]==2.0.36

# Utilities
pydantic==2.10.4
pydantic-settings==2.7.0
python-dotenv==1.0.1
aiofiles==24.1.0

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Development
httpx==0.28.1
pytest==8.3.4
pytest-asyncio==0.25.0
```

### Phase 5: Update Message Events

#### 5.1 Update message_start Event
**File:** `app/services/agent_service.py`

```python
yield ChatStreamEvent(
    event_type="message_start",
    data={
        "agent_id": agent_id,
        "model": self.model,  # e.g., "gpt-4"
        "provider": "Letta",
        "memory_enabled": True,
        "memory_blocks": memory_config
    }
)
```

### Phase 6: Testing

#### 6.1 Create Letta Agent
Before testing, create an agent in Letta:

```bash
# Using Letta CLI or API
letta create agent \
  --name evolving-assistant \
  --model gpt-4 \
  --memory-blocks human,persona,preferences,knowledge
```

Or programmatically:
```python
from agentic_learning import AgenticLearning

client = AgenticLearning()
agent = client.agents.create(
    name="evolving-assistant",
    model="gpt-4",
    memory_blocks=["human", "persona", "preferences", "knowledge"]
)
```

#### 6.2 Test Chat with Memory
```bash
# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Wait for services
sleep 15

# Test chat
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! My name is Mikus.",
    "conversation_id": "test-letta-memory"
  }'

# Test memory persistence (second message)
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is my name?",
    "conversation_id": "test-letta-memory"
  }'
```

Expected: AI should remember "Mikus" from the first conversation.

#### 6.3 Verify Memory Blocks
```python
from agentic_learning import AgenticLearning

client = AgenticLearning()
agent = client.agents.get(name="evolving-assistant")

# Check memory blocks
memory = client.memory.get(agent=agent.id)
print("Human memory:", memory.blocks["human"])
print("Persona memory:", memory.blocks["persona"])
```

### Phase 7: Update Documentation

#### 7.1 Update README.md
- Remove OpenRouter setup instructions
- Add Letta account setup instructions
- Update architecture diagram
- Update environment variables section

#### 7.2 Update DEBUGGING.md
- Remove Claude Code Router debugging steps
- Add Letta API connection debugging
- Update test commands to use Letta models

#### 7.3 Update Integration Tests
**File:** `tests/integration/test-chat.sh`

Update expected responses to reflect Letta provider:
```bash
# Check for Letta provider in response
if grep -q '"provider": "Letta"' "$temp_file"; then
    print_result 0 "Using Letta provider"
fi
```

## Trade-offs

### Advantages ✅
- **Full memory persistence**: Letta can save all conversation turns
- **Continual learning**: Memory blocks update automatically
- **Native integration**: No provider compatibility issues
- **Simpler architecture**: No need for Claude Code Router
- **Official support**: Using Letta as intended

### Disadvantages ❌
- **No DeepSeek v3.2**: Limited to Letta-supported models (GPT-4, Claude, etc.)
- **Cost**: GPT-4 is more expensive than DeepSeek
- **Model limitations**: Can't use latest open-source models
- **Vendor lock-in**: Dependent on Letta's model support
- **No WebSearch**: Letta doesn't support Anthropic's web search tool

## Available Models on Letta

Letta supports the following LLM providers:
- **OpenAI**: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- **Anthropic**: claude-3-opus, claude-3-sonnet, claude-3-haiku
- **Groq**: llama-3-70b, mixtral-8x7b
- **Local models**: via Ollama integration

**Recommended:** `gpt-4` or `claude-3-opus` for best results with tool use.

## Migration Checklist

- [ ] Update `.env` with Letta credentials
- [ ] Remove OpenRouter API key
- [ ] Update `app/config.py` settings
- [ ] Refactor `app/services/agent_service.py`
- [ ] Remove Claude Code Router from `docker-compose.yml`
- [ ] Update `scripts/start-services.sh`
- [ ] Update `requirements.txt`
- [ ] Create Letta agent via API or CLI
- [ ] Rebuild Docker container
- [ ] Test chat functionality
- [ ] Test memory persistence
- [ ] Verify memory blocks are updating
- [ ] Update documentation
- [ ] Update integration tests
- [ ] Commit changes to feature branch

## Estimated Time

- Configuration changes: 30 minutes
- Code refactoring: 1 hour
- Testing and debugging: 1-2 hours
- Documentation updates: 30 minutes

**Total:** 3-4 hours

## Next Steps

1. Obtain Letta API key from https://app.letta.com
2. Choose preferred model (gpt-4 recommended)
3. Follow Phase 1-7 implementation steps
4. Test thoroughly with memory persistence scenarios
5. Update documentation and commit changes

## Alternative: Hybrid Approach

If you want both DeepSeek and memory persistence, consider:
- Use DeepSeek for general chat (fast, cheap)
- Use Letta + GPT-4 for memory-critical conversations
- Implement routing logic based on conversation type
- Store conversation summaries in local database

This would require more complex implementation but provides best of both worlds.
