# Claude Code Router Integration

This directory contains the configuration and Dockerfile for integrating [claude-code-router](https://github.com/musistudio/claude-code-router) with the AI Companion Server.

## What is Claude Code Router?

Claude Code Router is a proxy service that allows you to:
- **Route requests to different AI models** based on task type (background, thinking, long context, etc.)
- **Support multiple providers** (Anthropic, OpenRouter, Ollama, custom endpoints)
- **Switch models dynamically** using `/model` command in Claude Code
- **Transform requests/responses** for different providers

## Architecture

```
┌─────────────────┐
│  Claude Code    │
│   (Desktop)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   AI Companion Container        │
│  ┌─────────────────────────┐   │
│  │ Claude Code Router :3000│   │
│  └───────────┬─────────────┘   │
│              │                  │
│  ┌───────────▼─────────────┐   │
│  │ FastAPI Server :8000    │   │
│  │ (Letta + Claude Agent)  │   │
│  └─────────────────────────┘   │
└─────────────┬───────────────────┘
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌──────────┐ ┌──────┐ ┌────────┐
│Anthropic │ │OpenR.│ │ Ollama │ :11434
└──────────┘ └──────┘ └────────┘
```

## Configuration

### `config.json`

The router configuration supports:

**Providers:**
- `anthropic` - Direct Anthropic API
- `openrouter` - OpenRouter for multiple models
- `ollama` - Local Ollama models
- `local-companion` - Your AI Companion Server

**Routing Rules:**
- `default` - Default model for all requests
- `background` - Fast local model for background tasks
- `think` - Reasoning model for complex tasks
- `longContext` - Model for long context (>60k tokens)
- `companion` - Route to local AI Companion Server

### Environment Variables

Required in `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...  # Optional
ROUTER_API_KEY=your-secret-key
```

## Usage

### Start Services

```bash
# Start all services (single container with router + FastAPI, plus ollama)
docker-compose up -d

# View logs
docker-compose logs -f ai-companion

# Check service health
curl http://localhost:8000/health  # FastAPI
curl http://localhost:3000/health  # Router
```

### Connect Claude Code

On your local machine:

```bash
# Install Claude Code Router CLI
npm install -g @musistudio/claude-code-router

# Configure to use Docker router
ccr activate http://localhost:3000 your-secret-key

# Start Claude Code with router
ccr code
```

### Switch Models

Inside Claude Code:

```
/model                           # List available models
/model background                # Switch to background model (Ollama)
/model think                     # Switch to thinking model (DeepSeek)
/model companion                 # Switch to AI Companion Server
/model anthropic,claude-sonnet-4 # Direct model selection
```

## Model Routing Strategy

| Task Type | Model | Provider | Use Case |
|-----------|-------|----------|----------|
| **Default** | Claude Sonnet 4 | Anthropic | General coding tasks |
| **Background** | Qwen 2.5 Coder | Ollama (local) | Fast, simple tasks |
| **Think** | DeepSeek Chat | OpenRouter | Complex reasoning |
| **Long Context** | Gemini 2.5 Pro | OpenRouter | Large codebases |
| **Companion** | Custom Agent | Local Server | Persistent memory tasks |

## Customization

Edit `config.json` to:
- Add new providers
- Configure custom models
- Adjust routing rules
- Set API timeouts
- Enable/disable logging

After changes:
```bash
docker-compose restart claude-code-router
```

## Troubleshooting

**Router not starting:**
```bash
docker-compose logs claude-code-router
```

**Connection refused:**
- Check `ROUTER_API_KEY` matches in `.env` and `ccr activate`
- Verify port 3000 is not in use

**Model not available:**
```bash
# Inside container
docker exec -it claude-code-router ccr model list
```

## Advanced Features

### GitHub Actions Integration

Use the router in CI/CD:

```yaml
- name: Run Claude Code Task
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    ccr activate http://router:3000 ${{ secrets.ROUTER_API_KEY }}
    ccr code --task "Review and fix security issues"
```

### Custom Transformers

Add custom request/response transformers in `config.json`:

```json
{
  "transformer": {
    "use": ["custom-transformer"],
    "custom-transformer": {
      "request": "path/to/transformer.js",
      "response": "path/to/transformer.js"
    }
  }
}
```

## Resources

- [Claude Code Router GitHub](https://github.com/musistudio/claude-code-router)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code/quickstart)
- [OpenRouter Models](https://openrouter.ai/models)
