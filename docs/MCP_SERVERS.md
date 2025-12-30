# MCP Server Integration

This server integrates with Model Context Protocol (MCP) servers to extend the AI agent's capabilities beyond native tools.

## Available MCP Servers

### Todoist

Task management integration via [Todoist MCP Server](https://github.com/abhiz123/todoist-mcp-server).

**Capabilities:**
- Create, read, update, and delete tasks
- Manage projects and sections
- Handle task labels and priorities
- Set due dates and recurring tasks
- Complete and uncomplete tasks

## Configuration

### 1. Get Todoist API Token

1. Go to [Todoist Settings](https://todoist.com/prefs/integrations)
2. Scroll to "API token" section
3. Copy your API token

### 2. Add to Environment

```bash
# .env file
TODOIST_API_TOKEN=your_todoist_api_token_here
```

### 3. MCP Server Config

Configuration is automatically loaded from `config/mcp_servers.json`:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "npx",
      "args": ["-y", "@abhiz123/todoist-mcp-server"],
      "env": {
        "TODOIST_API_TOKEN": "${TODOIST_API_TOKEN}"
      }
    }
  }
}
```

## Usage

Once configured, the agent can use Todoist functions directly:

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Add a task: Review PR #123 by tomorrow at 3pm",
    "conversation_id": "todo-1"
  }'

# Agent will use Todoist MCP to create the task
```

### Example Commands

**Create Tasks:**
- "Add a task to buy groceries tomorrow"
- "Create a high-priority task: Fix production bug"
- "Add 'Write documentation' to my Work project"

**List Tasks:**
- "Show me my tasks for today"
- "What tasks do I have in my Work project?"
- "List all high-priority tasks"

**Update Tasks:**
- "Mark 'Buy groceries' as complete"
- "Change the due date of 'Review PR' to Friday"
- "Update priority of 'Fix bug' to high"

**Projects:**
- "Create a new project called 'Q1 Planning'"
- "List all my projects"
- "Archive the 'Old Project' project"

## Adding More MCP Servers

### 1. Add Server Configuration

Edit `config/mcp_servers.json`:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "npx",
      "args": ["-y", "@abhiz123/todoist-mcp-server"],
      "env": {
        "TODOIST_API_TOKEN": "${TODOIST_API_TOKEN}"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### 2. Add Environment Variables

Update `app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings
    github_token: str = ""
```

Update `.env.example`:

```bash
GITHUB_TOKEN=your_github_token_here
```

### 3. Set Environment in Agent Service

Update `app/services/agent_service.py`:

```python
def _get_agent_options(self) -> ClaudeAgentOptions:
    # Set environment variables for MCP servers
    if settings.todoist_api_token:
        os.environ["TODOIST_API_TOKEN"] = settings.todoist_api_token
    if settings.github_token:
        os.environ["GITHUB_TOKEN"] = settings.github_token
    
    return ClaudeAgentOptions(
        # ... other options
        mcp_config_path="./config/mcp_servers.json",
    )
```

## Popular MCP Servers

### Productivity
- **Todoist** - Task management
- **Google Calendar** - Calendar integration
- **Notion** - Note-taking and databases
- **Slack** - Team communication

### Development
- **GitHub** - Repository management
- **GitLab** - Code hosting and CI/CD
- **Linear** - Issue tracking
- **Sentry** - Error monitoring

### Data & Search
- **PostgreSQL** - Database queries
- **Brave Search** - Web search
- **Google Drive** - File storage
- **Puppeteer** - Web automation

### AI & Analysis
- **Memory** - Knowledge graph storage
- **EverArt** - Image generation
- **Sequential Thinking** - Chain-of-thought reasoning

## Troubleshooting

### MCP Server Not Loading

**Check logs for:**
```
Error: Cannot find module '@abhiz123/todoist-mcp-server'
```

**Solution:** Ensure Node.js and npm are installed:
```bash
node --version  # Should be v18+
npm --version
```

### API Token Issues

**Check environment:**
```python
import os
print(os.getenv("TODOIST_API_TOKEN"))  # Should not be empty
```

**Solution:** Verify `.env` file is loaded and token is set.

### Tool Not Available

**Check Claude SDK logs for:**
```
Available tools: [...]
```

**Solution:** Restart server to reload MCP configuration:
```bash
./start-local.sh
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│           AI Companion Server (FastAPI)         │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │      Claude Agent SDK Client             │  │
│  │  ┌────────────────────────────────────┐  │  │
│  │  │    Native Tools                    │  │  │
│  │  │  - Bash, Read, Write, Edit, etc.  │  │  │
│  │  └────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────┐  │  │
│  │  │    MCP Servers (via config)        │  │  │
│  │  │  - Todoist (npx subprocess)        │  │  │
│  │  │  - GitHub (future)                 │  │  │
│  │  │  - etc.                            │  │  │
│  │  └────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
         │                    │
         ↓                    ↓
  ┌─────────────┐      ┌──────────────┐
  │ Letta Memory│      │ Todoist API  │
  └─────────────┘      └──────────────┘
```

## Best Practices

1. **Keep tokens secure**: Never commit `.env` file with real tokens
2. **Test MCP servers**: Use `npx @abhiz123/todoist-mcp-server` standalone first
3. **Monitor logs**: Check server logs for MCP initialization errors
4. **Version pinning**: Use specific versions in production (`@abhiz123/todoist-mcp-server@1.0.0`)
5. **Graceful fallback**: Agent should handle MCP server unavailability

## Resources

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Servers Directory](https://github.com/modelcontextprotocol/servers)
- [Claude Agent SDK MCP Docs](https://platform.claude.com/docs/en/agent-sdk/mcp)
- [Todoist MCP Server](https://github.com/abhiz123/todoist-mcp-server)
