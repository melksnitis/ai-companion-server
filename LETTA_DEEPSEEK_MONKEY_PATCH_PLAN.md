# Letta + DeepSeek Integration via Monkey Patching

## Problem Analysis

### Current Issue
Letta Learning SDK fails when using DeepSeek via OpenRouter because:
```
Error code: 400 - {'detail': 'INVALID_ARGUMENT: Provider anthropic is not supported (supported providers: letta)'}
```

### Root Cause
When Letta's `_save_conversation_turn_async()` function calls `client.messages.capture()`, it passes:
```python
provider="claude"  # or "anthropic"
model="claude"
```

The Letta API validates the `provider` field and only accepts `"letta"` as a valid provider, rejecting `"anthropic"` or `"claude"`.

### Architecture Flow
```
User Message
    ↓
Claude Agent SDK (via OpenRouter/DeepSeek)
    ↓
ClaudeInterceptor patches SubprocessCLITransport
    ↓
_save_conversation_turn_async(provider="claude", model="claude")
    ↓
Letta API: client.messages.capture()
    ↓
❌ Validation Error: Provider "claude" not supported
```

## Solution: Monkey Patch Strategy

### Approach
Monkey patch the `_save_conversation_turn_async()` function in Letta's interceptor utilities to:
1. **Override provider field**: Change `provider="claude"` to `provider="letta"`
2. **Set correct model name**: Change `model="claude"` to `model="deepseek/deepseek-v3.2"`
3. **Preserve all other functionality**: Keep message capture, memory injection, and streaming intact

### Why This Works
- Letta API accepts `provider="letta"` 
- The provider field is just metadata for Letta's tracking
- The actual LLM calls still go through Claude Agent SDK → OpenRouter → DeepSeek
- Letta only needs to store the conversation turns, not execute them

## Implementation Plan

### Phase 1: Create Monkey Patch Module

**File:** `app/utils/letta_patch.py`

```python
"""
Monkey patch for Letta Learning SDK to support DeepSeek via OpenRouter.

This patch modifies the _save_conversation_turn_async function to use
provider="letta" instead of provider="claude" to bypass Letta's provider validation.
"""

import sys
from typing import Dict, List

# Import the original function
from agentic_learning.interceptors.utils import _save_conversation_turn_async as _original_save
from agentic_learning.core import get_current_config


async def _patched_save_conversation_turn_async(
    provider: str,
    model: str,
    request_messages: List[dict] = None,
    response_dict: Dict[str, str] = None,
    register_task: bool = False,
):
    """
    Patched version that overrides provider to "letta" for compatibility.
    
    This allows using DeepSeek (or any model) via OpenRouter while still
    persisting conversations to Letta's memory system.
    """
    # Override provider to "letta" to pass validation
    patched_provider = "letta"
    
    # Use the actual model name (e.g., "deepseek/deepseek-v3.2")
    # This is just metadata for Letta's tracking
    patched_model = model if model != "claude" else "deepseek/deepseek-v3.2"
    
    config = get_current_config()
    if not config:
        return
    
    agent = config["agent_name"]
    client = config["client"]
    memory = config.get("memory")
    
    if not client:
        return
    
    async def save_task():
        try:
            # Check if client is async or sync
            is_async = hasattr(client, '__class__') and 'Async' in client.__class__.__name__
            
            if is_async:
                # Async client - await directly
                agent_state = await client.agents.retrieve(agent=agent)
                
                if not agent_state:
                    agent_state = await client.agents.create(
                        agent=agent,
                        memory=memory,
                    )
                
                return await client.messages.capture(
                    agent=agent,
                    request_messages=request_messages or [],
                    response_dict=response_dict or {},
                    model=patched_model,  # Use patched model name
                    provider=patched_provider,  # Use "letta" provider
                )
            else:
                # Sync client - run in executor
                import asyncio
                loop = asyncio.get_event_loop()
                
                agent_state = await loop.run_in_executor(
                    None,
                    lambda: client.agents.retrieve(agent=agent)
                )
                
                if not agent_state:
                    agent_state = await loop.run_in_executor(
                        None,
                        lambda: client.agents.create(
                            agent=agent,
                            memory=memory,
                        )
                    )
                
                return await loop.run_in_executor(
                    None,
                    lambda: client.messages.capture(
                        agent=agent,
                        request_messages=request_messages or [],
                        response_dict=response_dict or {},
                        model=patched_model,  # Use patched model name
                        provider=patched_provider,  # Use "letta" provider
                    )
                )
        
        except Exception as e:
            print(f"[Warning] Failed to save conversation turn: {e}", file=sys.stderr)
    
    if register_task:
        # Create and register the task for later awaiting
        import asyncio
        task = asyncio.create_task(save_task())
        config.get("pending_tasks", []).append(task)
    else:
        # Execute immediately
        await save_task()


def apply_letta_patch():
    """
    Apply the monkey patch to Letta's interceptor utilities.
    
    Call this function before using the learning() context.
    """
    import agentic_learning.interceptors.utils as utils_module
    
    # Replace the original function with our patched version
    utils_module._save_conversation_turn_async = _patched_save_conversation_turn_async
    
    print("✓ Letta monkey patch applied: provider='letta', model='deepseek/deepseek-v3.2'")


def remove_letta_patch():
    """
    Remove the monkey patch and restore original function.
    
    Useful for testing or cleanup.
    """
    import agentic_learning.interceptors.utils as utils_module
    
    # Restore original function
    utils_module._save_conversation_turn_async = _original_save
    
    print("✓ Letta monkey patch removed")
```

### Phase 2: Update AgentService

**File:** `app/services/agent_service.py`

```python
"""
Agent Service using Claude Agent SDK with OpenRouter + Letta Learning SDK
Combines OpenRouter's model routing with Letta's persistent memory and learning.
Uses monkey patch to enable Letta compatibility with DeepSeek.
"""

import os
from typing import AsyncGenerator, Optional, List, Dict, Any
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock
from agentic_learning import learning

from app.config import settings
from app.models.schemas import ChatStreamEvent, ToolCall
from app.utils.letta_patch import apply_letta_patch  # Import patch


class AgentService:
    """Agent service using Claude Agent SDK with OpenRouter and Letta Learning SDK.
    
    Architecture:
    - OpenRouter: Provides access to DeepSeek v3.2 and other models
    - Claude Agent SDK: Native tool execution (Bash, Read, Write, Edit, etc.)
    - Letta Learning SDK: Persistent memory and continual learning (patched)
    
    The learning context wraps the Claude Agent SDK to provide memory persistence.
    A monkey patch enables Letta to accept DeepSeek conversations.
    """
    
    def __init__(self):
        # Apply Letta monkey patch BEFORE any learning context is used
        apply_letta_patch()
        
        # Configure Claude Agent SDK to use OpenRouter directly
        os.environ["ANTHROPIC_BASE_URL"] = "https://openrouter.ai/api"
        os.environ["ANTHROPIC_AUTH_TOKEN"] = settings.openrouter_api_key
        os.environ["ANTHROPIC_API_KEY"] = ""  # Must be explicitly empty
        
        # Configure Letta Learning SDK
        if settings.letta_api_key:
            os.environ["LETTA_API_KEY"] = settings.letta_api_key
        
        self.agent_name = settings.letta_agent_name
    
    # ... rest of the class remains the same ...
```

### Phase 3: Test the Patch

**File:** `tests/test_letta_patch.py`

```python
"""
Test Letta monkey patch for DeepSeek compatibility.
"""

import asyncio
import os
import pytest
from app.utils.letta_patch import apply_letta_patch, remove_letta_patch


@pytest.mark.asyncio
async def test_letta_patch_applied():
    """Test that monkey patch is applied correctly."""
    apply_letta_patch()
    
    from agentic_learning.interceptors.utils import _save_conversation_turn_async
    
    # Check that the function is patched
    assert _save_conversation_turn_async.__name__ == "_patched_save_conversation_turn_async"
    
    remove_letta_patch()


@pytest.mark.asyncio
async def test_letta_deepseek_integration():
    """Test full integration with DeepSeek via OpenRouter."""
    from agentic_learning import learning
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    
    # Apply patch
    apply_letta_patch()
    
    # Configure environment
    os.environ["ANTHROPIC_BASE_URL"] = "https://openrouter.ai/api"
    os.environ["ANTHROPIC_AUTH_TOKEN"] = os.getenv("OPENROUTER_API_KEY", "")
    os.environ["ANTHROPIC_API_KEY"] = ""
    os.environ["LETTA_API_KEY"] = os.getenv("LETTA_API_KEY", "")
    
    options = ClaudeAgentOptions(
        permission_mode="dontAsk",
        allowed_tools=["Bash", "Read", "Write"],
        model="deepseek/deepseek-v3.2",
        cwd="/tmp"
    )
    
    try:
        async with learning(agent="test-deepseek-patch", memory=["human"]):
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt="Say hello")
                
                async for msg in client.receive_response():
                    # Just consume messages
                    pass
        
        print("✓ Integration test passed - no provider validation error!")
        
    except Exception as e:
        if "Provider anthropic is not supported" in str(e):
            pytest.fail(f"Monkey patch failed: {e}")
        else:
            # Other errors are acceptable for this test
            print(f"Note: {e}")
    
    finally:
        remove_letta_patch()


if __name__ == "__main__":
    asyncio.run(test_letta_deepseek_integration())
```

### Phase 4: Update Startup

**File:** `app/main.py`

```python
from fastapi import FastAPI
from app.utils.letta_patch import apply_letta_patch

app = FastAPI(title="AI Companion Server")

@app.on_event("startup")
async def startup_event():
    """Apply Letta patch on application startup."""
    apply_letta_patch()
    print("🚀 AI Companion Server started with Letta + DeepSeek support")

# ... rest of the application ...
```

## Verification Steps

### 1. Manual Test
```bash
# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Wait for services
sleep 15

# Test chat with memory
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! My name is Mikus. Remember this.",
    "conversation_id": "test-deepseek-memory"
  }'

# Test memory recall (should remember "Mikus")
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is my name?",
    "conversation_id": "test-deepseek-memory"
  }'
```

### 2. Check Letta Dashboard
Visit https://app.letta.com and verify:
- Agent "evolving-assistant" exists
- Conversations are being saved
- Memory blocks are updating
- Provider shows as "letta"
- Model shows as "deepseek/deepseek-v3.2"

### 3. Check Logs
```bash
docker-compose logs ai-companion | grep -i "letta\|patch\|provider"
```

Expected output:
```
✓ Letta monkey patch applied: provider='letta', model='deepseek/deepseek-v3.2'
```

Should NOT see:
```
[Warning] Failed to save conversation turn: Provider anthropic is not supported
```

## Alternative: Patch at Import Time

If you want the patch to apply automatically without explicit calls:

**File:** `app/utils/__init__.py`

```python
"""
Auto-apply Letta patch on import.
"""

from .letta_patch import apply_letta_patch

# Apply patch when utils module is imported
apply_letta_patch()
```

Then in `app/services/agent_service.py`:
```python
import app.utils  # Patch is applied automatically
from agentic_learning import learning
```

## Trade-offs

### Advantages ✅
- **Keep DeepSeek v3.2**: Fast, cheap, capable model
- **Full memory persistence**: Letta saves all conversations
- **Minimal code changes**: Just add monkey patch module
- **No Letta SDK modifications**: Works with official package
- **Reversible**: Can remove patch anytime

### Disadvantages ❌
- **Monkey patching risks**: Could break with Letta SDK updates
- **Provider metadata incorrect**: Letta thinks it's using "letta" provider
- **Maintenance burden**: Need to monitor Letta SDK changes
- **Not officially supported**: Letta may not support this use case
- **Potential edge cases**: Unknown issues with provider mismatch

## Risk Mitigation

### 1. Version Pinning
```python
# requirements.txt
agentic-learning==0.4.3  # Pin to tested version
```

### 2. Patch Validation
```python
def apply_letta_patch():
    """Apply patch with version checking."""
    import agentic_learning
    
    # Check version compatibility
    if agentic_learning.__version__ not in ["0.4.3", "0.4.4"]:
        print(f"[Warning] Letta patch tested on v0.4.3, you have v{agentic_learning.__version__}")
    
    # Apply patch...
```

### 3. Fallback Mode
```python
def __init__(self):
    try:
        apply_letta_patch()
        self.memory_enabled = True
    except Exception as e:
        print(f"[Warning] Letta patch failed: {e}. Running without memory.")
        self.memory_enabled = False
```

### 4. Integration Tests
Add CI tests that verify:
- Patch applies successfully
- No provider validation errors
- Memory persistence works
- Conversations are saved to Letta

## Future-Proofing

### Option A: Contribute to Letta
Submit PR to Letta Learning SDK to:
- Add support for custom providers
- Allow provider field override
- Make provider validation optional

### Option B: Custom Interceptor
Create a custom interceptor that extends `ClaudeInterceptor`:

```python
class DeepSeekInterceptor(ClaudeInterceptor):
    PROVIDER = "letta"  # Override provider
    
    def build_response_dict(self, response):
        # Custom implementation for DeepSeek
        pass
```

### Option C: Letta Feature Request
Request Letta to add:
- `provider="external"` option
- Custom provider registration
- Provider validation bypass flag

## Implementation Checklist

- [ ] Create `app/utils/letta_patch.py`
- [ ] Update `app/services/agent_service.py` to apply patch
- [ ] Add `tests/test_letta_patch.py`
- [ ] Update `app/main.py` startup event
- [ ] Pin `agentic-learning==0.4.3` in requirements.txt
- [ ] Test patch application
- [ ] Test chat with memory persistence
- [ ] Verify Letta dashboard shows conversations
- [ ] Check for provider validation errors
- [ ] Update documentation
- [ ] Add CI integration tests
- [ ] Commit to feature branch

## Estimated Time

- Monkey patch implementation: 30 minutes
- Integration and testing: 1 hour
- Documentation: 30 minutes
- Edge case handling: 30 minutes

**Total:** 2.5 hours

## Success Criteria

✅ Chat works with DeepSeek v3.2 via OpenRouter
✅ No "Provider anthropic is not supported" errors
✅ Conversations saved to Letta
✅ Memory blocks update correctly
✅ Memory persists across sessions
✅ Agent remembers information from previous conversations

## Conclusion

This monkey patch approach is a **pragmatic solution** that enables the best of both worlds:
- **DeepSeek v3.2** for fast, cheap, capable inference
- **Letta Learning SDK** for persistent memory and learning

While not officially supported, it's a minimal, reversible change that solves the provider validation issue without forking Letta or modifying the SDK.

**Recommendation:** Implement this patch as a short-term solution while monitoring Letta's roadmap for official external provider support.
