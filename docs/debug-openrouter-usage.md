# Debugging OpenRouter Usage

This guide documents how to figure out which local component is making paid OpenRouter requests (e.g., `anthropic/claude-4.5-haiku-20251001`) even when the FastAPI server is configured to use the free `xiaomi/mimo-v2-flash:free` model.

---

## 🔴 ROOT CAUSE IDENTIFIED

**The Claude Code CLI has built-in agents that use Anthropic models regardless of your `--model` setting.**

Evidence from `~/.claude/telemetry/*.json`:
```json
{
  "model": "claude-sonnet-4-5-20250929",
  "is_built_in_agent": true,
  "querySource": "agent:builtin:Plan"
}
```

These built-in agents (like "Plan", "Task") make their own API calls using Claude models even when you configure a different model like `xiaomi/mimo-v2-flash:free`.

### Root Cause: Built-in Subagents

The Claude CLI has **built-in subagents** with hardcoded models:
- **Explore subagent** → Uses **Haiku** (~20 parallel calls per request for context indexing)
- **Plan subagent** → Uses **Sonnet**
- **General-purpose subagent** → Uses **Sonnet**

The `settings.json` `model` field only affects the main conversation, not these internal subagents.

### Solution 1: Override Built-in Subagents

Create custom agents in `~/.claude/agents/` with `model: "inherit"` to override the built-in ones:

**~/.claude/agents/explore.md**
```markdown
---
name: explore
description: Fast codebase exploration and file searching.
tools: Glob, Grep, Read, Bash
model: inherit
---
You are an exploration agent. Search the codebase efficiently.
```

**~/.claude/agents/plan.md**
```markdown
---
name: plan
description: Research and analyze codebase for implementation plans.
tools: Read, Glob, Grep, Bash
model: inherit
---
You are a planning agent. Research the codebase to gather context.
```

### Solution 2: Configure settings.json

Create `~/.claude/settings.json`:
```json
{
  "model": "xiaomi/mimo-v2-flash:free",
  "permissions": {
    "defaultMode": "dontAsk"
  }
}
```

### Additional Workarounds

1. **Use a separate API key** with spending limits for the Claude CLI
2. **Monitor and alert** on unexpected model usage via OpenRouter dashboard
3. **Set spending cap** to $0 on OpenRouter to block any paid model calls

---

## 1. Confirm what the FastAPI service sends

We already instrumented the backend so its logs prove the chosen model:

- `app/services/agent_service.py` prints `[AgentService] _get_agent_options using model=…` before creating `ClaudeAgentOptions`.
- `_get_configured_model()` in `letta-sdk/python/src/agentic_learning/interceptors/utils.py` logs `[LettaSDK] _get_configured_model -> … (source=…)`.
- The Claude interceptor only falls back to the Xiaomi slug when saving to Letta; Anthropic defaults were removed.

If these logs always show Xiaomi but the OpenRouter CSV still lists Haiku/Sonnet, those paid calls are coming from **another process sharing the same API key**.

---

## 2. Use OpenRouter's generation API for attribution

Every row in `openrouter_activity_YYYY-MM-DD.csv` has a `generation_id`. Fetch the full metadata:

```bash
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  "https://openrouter.ai/api/v1/generation?id=$GENERATION_ID" | jq
```

The response contains:
- `request`: headers (including `http_referer` if set) and request body (model, params).
- `app_id` / `api_key_name`: which OpenRouter app paid for the call.

Use this whenever a suspicious charge appears.

---

## 3. Isolate local processes

### 3.1 Rotate to a new API key

1. Create a fresh OpenRouter key in the dashboard.
2. Update `.env` with the new key.
3. Restart everything and re-test.
4. If Haiku charges disappear, the previous key was used by another service.

### 3.2 Run components one at a time

| Step | Command | Expected log |
|------|---------|--------------|
| FastAPI only | `./start-local.sh` then `curl /chat/stream` | `model=xiaomi/mimo-v2-flash:free` |
| Letta SDK demo | `python letta-sdk/examples/claude_research_agent/test_hooks.py` | Should now use `_get_configured_model()` |
| Claude Code Router | Check `router/config.json` or router env | Must reference Xiaomi slug |

### 3.3 Compare with/without Letta wrapper

Create two minimal test scripts:

**test_with_letta.py**
```python
import asyncio
from agentic_learning import learning
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Bash"],
        model="xiaomi/mimo-v2-flash:free"
    )
    async with learning(agent="debug-test"):
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt="echo hello")
            async for msg in client.receive_response():
                print(msg)

asyncio.run(main())
```

**test_without_letta.py**
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Bash"],
        model="xiaomi/mimo-v2-flash:free"
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt="echo hello")
        async for msg in client.receive_response():
            print(msg)

asyncio.run(main())
```

Run each and compare OpenRouter CSV afterwards. If **both** show Xiaomi, Letta is not the issue. If one shows Haiku, that path has a hardcoded model somewhere.

---

## 4. Add optional request tracing

### HTTP Proxy (mitmproxy)

```bash
# Terminal 1
mitmproxy --mode regular@8080

# Terminal 2
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
./start-local.sh
```

All OpenRouter calls will appear in the mitmproxy UI with full payloads.

### Python-level logging

Add to your entrypoint:
```python
import httpx
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)
```

Or patch `requests`/`httpx` to log every outgoing call.

---

## 5. Prevent future surprises

1. **Dedicated keys per service**: separate OpenRouter keys for FastAPI, router, demos.
2. **Spending caps**: set $0 daily limit on free-only keys so paid calls fail fast.
3. **CI guardrail**: lint for `model="haiku"` / `"sonnet"` literals; fail build if found.
4. **Runtime assertion**: verify `settings.openrouter_model_id` is in the free-model list before making requests.

---

## 6. Troubleshooting checklist

- [ ] FastAPI logs show Xiaomi but CSV shows Haiku? → Another consumer uses the key.
- [ ] `GET /api/v1/generation?id=…` reveals different `http_referer`? → Track that client.
- [ ] After rotating key, paid calls stop? → Old key compromised/used elsewhere.
- [ ] Scripts without Letta wrapper honor `OPENROUTER_MODEL_ID`? → Update them to use `_get_configured_model()`.
- [ ] Claude Code Router running with own config? → Ensure it references Xiaomi slug.

---

## 7. Ready-made test scripts

We've created isolated test scripts to help pinpoint the issue:

```bash
# Test WITH Letta wrapper
python scripts/test_with_letta.py

# Test WITHOUT Letta wrapper  
python scripts/test_without_letta.py

# Check a specific generation from OpenRouter CSV
python scripts/check_openrouter_generation.py gen-1767116740-7lrapuv3INfw6BtjwpRq
```

Compare the OpenRouter activity CSV after running each script. If both show `xiaomi/mimo-v2-flash`, then neither the raw Claude SDK nor the Letta interceptor is the culprit—look elsewhere (router, other processes).

---

## 8. Quick commands

```bash
# Check recent generations for a specific model
grep "claude-4.5-haiku" openrouter_activity_*.csv | head -5

# Fetch generation details
export GEN_ID="gen-1767116740-7lrapuv3INfw6BtjwpRq"
curl -s -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  "https://openrouter.ai/api/v1/generation?id=$GEN_ID" | jq '.request.model, .request.headers'

# List all processes using OpenRouter (approximate)
lsof -i :443 | grep openrouter
```

Following this playbook should identify the exact process issuing Haiku/Sonnet requests and keep the local environment on the free tier.
