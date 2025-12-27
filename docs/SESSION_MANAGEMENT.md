# Session Management & Memory Integration

This AI Companion Server integrates **Claude Agent SDK** for native conversation sessions with **Letta Learning SDK** for long-term memory persistence.

## Architecture

### Two-Layer Memory System

1. **Short-term (Claude SDK Sessions)**
   - Native conversation history within a session
   - Tool usage context and file edits
   - Managed by Claude Code subprocess
   - Persists until session ends

2. **Long-term (Letta Memory)**
   - Cross-session facts and context
   - Memory blocks: `human`, `persona`, `preferences`, `knowledge`
   - Stored in Letta database
   - Persists indefinitely

## Session Behavior

### Automatic Session Management

By default, sessions are automatically managed:

```bash
# First message - creates new session
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My favorite color is blue",
    "conversation_id": "conv-123"
  }'

# Response includes session_id event:
# data: {"event": "session_id", "data": {"session_id": "4dc88e4a-..."}}

# Second message - automatically resumes session
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is my favorite color?",
    "conversation_id": "conv-123"
  }'

# Agent remembers: "You said your favorite color is blue"
```

The session ID is:
- Captured from Claude SDK on first message
- Stored in database with `conversation_id`
- Automatically resumed on subsequent messages

### Explicit Session Control

Override automatic behavior by passing `session_id`:

#### Resume Specific Session
```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Continue where we left off",
    "conversation_id": "conv-456",
    "session_id": "4dc88e4a-26d5-42f9-b58b-88bb880bbad2"
  }'
```

#### Fork Session (New Branch)
```bash
# Start fresh conversation while keeping conversation_id
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Let me try a different approach",
    "conversation_id": "conv-123",
    "session_id": null
  }'
```

#### Force Fresh Session
```bash
# Pass empty string to ignore stored session
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Start completely fresh",
    "conversation_id": "conv-123",
    "session_id": ""
  }'
```

## Session Priority

Session ID resolution follows this priority:

1. **Request `session_id`** (highest priority)
2. **Database stored session** (from previous messages)
3. **None** (creates new session)

This allows:
- ✅ Automatic continuation by default
- ✅ Explicit resumption when needed
- ✅ Session forking for experimentation
- ✅ Fresh starts while keeping conversation_id

## Memory Integration

### What Gets Remembered

**Claude SDK Session (Short-term)**
- Exact conversation turns
- Tool calls and outputs
- File modifications
- Intermediate reasoning

**Letta Memory (Long-term)**
- User's name and preferences
- Important facts learned
- Personality traits
- Knowledge accumulated

### Memory Injection Flow

```
1. Request arrives
2. [Letta] Retrieve memory blocks for agent
3. [Interceptor] Inject memory into system prompt
4. [Claude SDK] Initialize subprocess with memory
5. [Claude SDK] Load session history (if resuming)
6. LLM sees: Memory + Session History + New Message
7. [Letta] Save conversation turn for learning
8. [Database] Store session_id for future resumption
```

## API Reference

### POST `/chat/stream`

**Request Body:**
```typescript
{
  message: string;              // User message (required)
  conversation_id?: string;     // Conversation identifier (auto-generated if omitted)
  session_id?: string | null;   // Claude SDK session ID (auto-managed if omitted)
  include_memory?: boolean;     // Enable Letta memory (default: true)
  tools_enabled?: boolean;      // Enable tool usage (default: true)
  stream?: boolean;             // Stream response (default: true)
}
```

**Response Events:**
```typescript
// Session ID captured/resumed
data: {"event": "session_id", "data": {"session_id": "..."}}

// Conversation identifier
data: {"event": "conversation_id", "data": {"id": "..."}}

// Message streaming
data: {"event": "content_delta", "data": {"text": "..."}}

// Completion
data: {"event": "done", "data": {}}
```

## Use Cases

### 1. Multi-Turn Coding Assistant
```bash
# Turn 1: Start task
curl -X POST http://localhost:8000/chat/stream -d '{
  "message": "Create a Python web server",
  "conversation_id": "coding-task-1"
}'

# Turn 2: Continue (auto-resumes session)
curl -X POST http://localhost:8000/chat/stream -d '{
  "message": "Add authentication",
  "conversation_id": "coding-task-1"
}'

# Turn 3: Continue (remembers all context)
curl -X POST http://localhost:8000/chat/stream -d '{
  "message": "Write tests for it",
  "conversation_id": "coding-task-1"
}'
```

### 2. Session Forking for Experiments
```bash
# Main conversation
curl -X POST http://localhost:8000/chat/stream -d '{
  "message": "Build a REST API",
  "conversation_id": "api-project"
}'
# Captures session_id: "session-A"

# Fork to try different approach
curl -X POST http://localhost:8000/chat/stream -d '{
  "message": "Actually, use GraphQL instead",
  "conversation_id": "api-project",
  "session_id": null
}'
# Creates new session_id: "session-B"

# Resume original approach
curl -X POST http://localhost:8000/chat/stream -d '{
  "message": "Continue with REST",
  "conversation_id": "api-project",
  "session_id": "session-A"
}'
```

### 3. Cross-Conversation Memory
```bash
# Conversation 1: Teach preference
curl -X POST http://localhost:8000/chat/stream -d '{
  "message": "I prefer TypeScript over JavaScript",
  "conversation_id": "pref-learning"
}'

# Conversation 2: Later, different session
curl -X POST http://localhost:8000/chat/stream -d '{
  "message": "Create a web project",
  "conversation_id": "new-project"
}'
# Agent uses TypeScript (remembers from Letta memory)
```

## Configuration

### Environment Variables

```bash
# Letta Configuration
LETTA_API_KEY=your_letta_api_key
LETTA_BASE_URL=http://localhost:8283  # Self-hosted Letta server

# OpenRouter Configuration (for DeepSeek v3)
OPENROUTER_API_KEY=your_openrouter_key

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/conversations.db
```

### Memory Blocks

Configure which memory blocks to use:

```bash
curl -X POST http://localhost:8000/chat/stream -d '{
  "message": "Hello",
  "conversation_id": "test",
  "memory_labels": ["human", "persona", "preferences"]
}'
```

Available blocks:
- `human` - User information
- `persona` - Agent personality
- `preferences` - User preferences
- `knowledge` - Learned facts
- `reflection` - Agent self-reflection

## Troubleshooting

### Session Not Resuming

**Check logs for:**
```
[SESSION] Resuming session: <session-id>
[WRITE] Sending data to subprocess: ... "session_id": "<session-id>"
```

**Common issues:**
- Database not persisting `extra_data`
- Session ID not captured (check `session_id` event)
- Passing wrong `conversation_id`

### Memory Not Appearing

**Check logs for:**
```
[INIT] Injecting memory before subprocess starts
[MEMORY] Retrieved context (length=XXX): <memory_blocks>...
[MEMORY] Set new system prompt
```

**Common issues:**
- `include_memory: false` in request
- Letta server not running
- Wrong `LETTA_BASE_URL`
- Agent not found in Letta (auto-created on first use)

### Session ID vs Conversation ID

- **`conversation_id`**: Your app's identifier (database key, UI grouping)
- **`session_id`**: Claude SDK's subprocess session (conversation history)
- One `conversation_id` can have multiple `session_id`s (forking)
- One `session_id` should map to one `conversation_id` (convention)

## Best Practices

1. **Let it auto-manage**: Don't pass `session_id` unless you need explicit control
2. **Use meaningful conversation IDs**: Makes debugging easier
3. **Enable memory by default**: Provides better user experience
4. **Fork for experiments**: Use `session_id: null` to try alternatives
5. **Monitor session_id events**: Track session creation in your UI
6. **Store session metadata**: Save session_id in your database for later resumption

## Implementation Details

### Session Capture
```python
# Python SDK: SystemMessage.data contains session_id
if isinstance(msg, SystemMessage) and msg.subtype == 'init':
    session_id = msg.data['session_id']
```

### Session Resumption
```python
# Pass session_id in ClaudeAgentOptions
options = ClaudeAgentOptions(
    resume=session_id,  # Resumes previous session
    model="deepseek/deepseek-v3.2",
    # ... other options
)
```

### Memory Injection
```python
# Happens in transport __init__ before subprocess starts
config = get_current_config()
memory_context = await client.memory.context.retrieve(agent=agent_id)
options.system_prompt = memory_context  # Injected before first message
```

## Related Documentation

- [Claude Agent SDK Sessions](https://platform.claude.com/docs/en/agent-sdk/sessions)
- [Letta Learning SDK](https://github.com/letta-ai/learning-sdk)
- [File Checkpointing](https://platform.claude.com/docs/en/agent-sdk/file-checkpointing)
