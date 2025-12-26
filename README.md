# Evolving Personal AI Assistant - Backend

A FastAPI-based backend for the Evolving Personal AI Assistant powered by **Letta Learning SDK** and **Claude Agent SDK** for persistent memory, continual learning, and agentic tool use.

## Architecture

Built on the **Letta Learning SDK** pattern (inspired by [claude_research_agent](https://github.com/letta-ai/learning-sdk/tree/main/examples/claude_research_agent)):

- **Claude Agent SDK**: Provides native tool execution (Bash, Read, Write, Edit, Search, Glob)
- **Letta Learning SDK**: Wraps agent calls to provide automatic memory persistence and retrieval
- **FastAPI**: Exposes streaming SSE and WebSocket endpoints for real-time interaction

## Features

- **Session Management**: Native Claude SDK session continuity with automatic resumption
- **Continual Learning**: Automatic memory persistence across sessions via Letta
- **Two-Layer Memory**: Short-term (session history) + Long-term (Letta memory blocks)
- **Streaming Chat**: Real-time streaming responses via SSE and WebSocket
- **Claude Agent SDK**: Native tool execution (Bash, Read, Write, Edit, Search, Glob)
- **Claude Code Router**: Intelligent model routing (DeepSeek, Claude, Gemini, local models)
- **Persistent Memory**: Letta-managed memory blocks (human, persona, preferences, knowledge)
- **Workspace Management**: File tree browsing and operations within a sandboxed workspace
- **Conversation History**: SQLite-backed conversation storage

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key
- Docker & Docker Compose (for containerized deployment)
- Node.js 20+ (for Claude Code Router CLI)

### Local Development

1. **Clone and setup**:
   ```bash
   cd ai-companion-server
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENROUTER_API_KEY and LETTA_API_KEY
   # Get OpenRouter API key at: https://openrouter.ai/keys
   # Get Letta API key at: https://app.letta.com
   # Note: Model selection is handled by Claude Code Router (see router/config.json)
   ```

3. **Run the server**:
   ```bash
   python -m app.main
   # Or with uvicorn directly:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the API**:
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

### Docker Deployment

**Standard deployment (AI Companion Server only):**
```bash
# Set your API keys in .env
cp .env.example .env
# Edit .env and add your keys

# Build and run
docker-compose up -d ai-companion
```

**Full deployment with Claude Code Router:**
```bash
# Run the setup script
./scripts/setup-router.sh

# Or manually:
docker-compose up -d
```

This starts:
- **AI Companion Container** - Single container running:
  - FastAPI backend (port 8000) - Letta + Claude Agent SDK
  - Claude Code Router (port 3000) - Model routing proxy
- **Ollama** (port 11434) - Local model inference (optional)

See `router/README.md` for Claude Code Router setup and usage.

## API Endpoints

### Chat

- `POST /chat/stream` - Stream a chat response (SSE)
- `GET /chat/conversations` - List conversations
- `GET /chat/conversations/{id}` - Get conversation details
- `DELETE /chat/conversations/{id}` - Delete a conversation

### Memory

- `GET /memory` - List memory blocks
- `POST /memory` - Create a memory block
- `GET /memory/context` - Get formatted memory context
- `GET /memory/search?q=query` - Search memories
- `POST /memory/upsert` - Create or update memory
- `PUT /memory/{id}` - Update a memory block
- `DELETE /memory/{id}` - Delete a memory block

### Workspace

- `GET /workspace/tree` - Get file tree
- `GET /workspace/files` - List files
- `GET /workspace/stats` - Get workspace statistics
- `GET /workspace/file?path=...` - Read a file

### Tools

- `GET /tools` - List available tools
- `POST /tools/execute` - Execute a tool
- `POST /tools/bash` - Execute a bash command

### WebSocket

Connect to `/ws` for real-time bidirectional communication.

**Actions**:
- `{"action": "chat", "message": "Hello"}` - Send a chat message
- `{"action": "get_memory"}` - Get memory context
- `{"action": "list_files", "path": "."}` - List files
- `{"action": "ping"}` - Health check

## Available Tools

The assistant has access to Claude Agent SDK native tools:

| Tool | Description |
|------|-------------|
| `Bash` | Execute shell commands in the workspace |
| `Read` | Read file contents |
| `Write` | Create or overwrite files |
| `Edit` | Find and replace text in files |
| `Glob` | List files matching patterns |
| `Search` | Search for patterns in files |

## Session Management

**Two-layer conversation continuity:**

1. **Short-term (Claude SDK Sessions)**: Native conversation history, tool context, file edits
2. **Long-term (Letta Memory)**: Cross-session facts, preferences, learned knowledge

### Automatic Behavior

Sessions are automatically managed by default:

```bash
# First message - creates session
curl -X POST http://localhost:8000/chat/stream \
  -d '{"message": "My favorite color is blue", "conversation_id": "conv-1"}'
# Returns: session_id event

# Second message - auto-resumes
curl -X POST http://localhost:8000/chat/stream \
  -d '{"message": "What is my favorite color?", "conversation_id": "conv-1"}'
# Agent remembers: "You said your favorite color is blue"
```

### Explicit Control

Pass `session_id` to override automatic behavior:

```bash
# Resume specific session
curl -X POST http://localhost:8000/chat/stream \
  -d '{
    "message": "Continue from where we left off",
    "conversation_id": "conv-1",
    "session_id": "4dc88e4a-26d5-42f9-b58b-88bb880bbad2"
  }'

# Start fresh (fork conversation)
curl -X POST http://localhost:8000/chat/stream \
  -d '{
    "message": "Try a different approach",
    "conversation_id": "conv-1",
    "session_id": null
  }'
```

**📖 See [docs/SESSION_MANAGEMENT.md](docs/SESSION_MANAGEMENT.md) for complete documentation**

## Memory System

Memory is automatically managed by **Letta Learning SDK**:

- **Automatic Capture**: All conversations are automatically captured
- **Semantic Retrieval**: Relevant context is injected into prompts based on memory labels
- **Persistent Across Sessions**: Memory persists even after server restarts
- **Memory Labels**: `human`, `persona`, `preferences`, `knowledge`
- **Per-Agent Isolation**: Each conversation ID maintains separate memory

## Project Structure

```
ai-companion-server/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application + WebSocket handler
│   ├── config.py         # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py    # Pydantic models
│   │   └── database.py   # SQLAlchemy models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py       # SSE streaming chat endpoint
│   │   ├── memory.py     # Memory endpoints
│   │   ├── workspace.py  # Workspace endpoints
│   │   └── tools.py      # Tool endpoints
│   └── services/
│       ├── __init__.py
│       ├── agent_service.py     # Simplified Claude Agent SDK + Letta wrapper
│       ├── memory_service.py    # Local memory management (SQLite)
│       └── workspace_service.py # Workspace file operations
├── router/
│   ├── config.json       # Router configuration
│   └── README.md         # Router documentation
├── scripts/
│   ├── setup-router.sh   # Router setup script
│   └── start-services.sh # Multi-service startup script
├── workspace/            # Sandboxed workspace directory
├── data/                 # Database storage
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Example Usage

### SSE Streaming Chat

```python
import httpx

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:8000/chat/stream",
        json={"message": "Hello, what can you help me with?"},
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                print(line[6:])
```

### WebSocket Chat

```javascript
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data.event, data.data);
};

ws.onopen = () => {
    ws.send(JSON.stringify({
        action: "chat",
        message: "Hello!"
    }));
};
```

## License

MIT
