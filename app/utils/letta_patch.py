"""
Monkey patch for Letta Learning SDK to support DeepSeek via OpenRouter.

Uses wrapt's post import hooks to patch modules BEFORE caching occurs.
"""

import sys
from typing import Dict, List
from agentic_learning.core import get_current_config

# Store original for restore
_original_save = None


async def _patched_save_conversation_turn_async(
    provider: str,
    model: str,
    request_messages: List[dict] = None,
    response_dict: Dict[str, str] = None,
    register_task: bool = False,
):
    """Patched version that overrides provider to 'letta'."""
    patched_provider = "letta"
    patched_model = model if model != "claude" else "deepseek/deepseek-v3.2"
    
    print(f"[PATCH DEBUG] Called with provider='{provider}' -> '{patched_provider}'", file=sys.stderr)
    
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
            is_async = hasattr(client, '__class__') and 'Async' in client.__class__.__name__
            
            if is_async:
                agent_state = await client.agents.retrieve(agent=agent)
                if not agent_state:
                    agent_state = await client.agents.create(agent=agent, memory=memory)
                
                print(f"[PATCH DEBUG] Calling capture with provider='{patched_provider}'", file=sys.stderr)
                result = await client.messages.capture(
                    agent=agent,
                    request_messages=request_messages or [],
                    response_dict=response_dict or {},
                    model=patched_model,
                    provider=patched_provider,
                )
                print(f"[PATCH DEBUG] Capture succeeded!", file=sys.stderr)
                return result
            else:
                import asyncio
                loop = asyncio.get_event_loop()
                
                agent_state = await loop.run_in_executor(
                    None,
                    lambda: client.agents.retrieve(agent=agent)
                )
                if not agent_state:
                    agent_state = await loop.run_in_executor(
                        None,
                        lambda: client.agents.create(agent=agent, memory=memory)
                    )
                
                return await loop.run_in_executor(
                    None,
                    lambda: client.messages.capture(
                        agent=agent,
                        request_messages=request_messages or [],
                        response_dict=response_dict or {},
                        model=patched_model,
                        provider=patched_provider,
                    )
                )
        
        except Exception as e:
            print(f"[PATCH DEBUG] Exception: {e}", file=sys.stderr)
            print(f"[Warning] Failed to save conversation turn: {e}", file=sys.stderr)
    
    if register_task:
        import asyncio
        task = asyncio.create_task(save_task())
        config.get("pending_tasks", []).append(task)
    else:
        await save_task()


def _patch_utils_module(utils_module):
    """Callback: Patch utils when imported."""
    global _original_save
    _original_save = utils_module._save_conversation_turn_async
    utils_module._save_conversation_turn_async = _patched_save_conversation_turn_async
    print(f"[PATCH] ✓ Patched utils._save_conversation_turn_async", file=sys.stderr)


def apply_letta_patch():
    """Apply patch using wrapt's post import hooks."""
    try:
        from wrapt import register_post_import_hook
    except ImportError:
        print("[PATCH] ❌ wrapt not installed", file=sys.stderr)
        return
    
    # Patch utils module
    register_post_import_hook(_patch_utils_module, 'agentic_learning.interceptors.utils')
    
    # Patch interceptors
    def patch_claude(module):
        module.PROVIDER = "letta"
        print(f"[PATCH] ✓ Patched ClaudeInterceptor.PROVIDER", file=sys.stderr)
    
    def patch_anthropic(module):
        module.PROVIDER = "letta"
        print(f"[PATCH] ✓ Patched AnthropicInterceptor.PROVIDER", file=sys.stderr)
    
    register_post_import_hook(patch_claude, 'agentic_learning.interceptors.claude')
    register_post_import_hook(patch_anthropic, 'agentic_learning.interceptors.anthropic')
    
    print("✓ Letta post import hooks registered: provider='letta'", file=sys.stderr)


def remove_letta_patch():
    """Remove patch and restore original."""
    global _original_save
    if _original_save:
        import agentic_learning.interceptors.utils as utils_module
        utils_module._save_conversation_turn_async = _original_save
        print("✓ Letta monkey patch removed", file=sys.stderr)
