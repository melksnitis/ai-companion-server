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
    
    Args:
        provider: Original provider (e.g., "claude", "anthropic")
        model: Original model name (e.g., "claude", "deepseek/deepseek-v3.2")
        request_messages: List of request messages
        response_dict: Response from provider
        register_task: If True, create and register task instead of awaiting directly
    """
    # Override provider to "letta" to pass validation
    patched_provider = "letta"
    
    # Use the actual model name for tracking
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
    
    This replaces the _save_conversation_turn_async function with our patched
    version that overrides provider="letta" to bypass validation.
    
    Call this function before using the learning() context.
    """
    import agentic_learning
    import agentic_learning.interceptors.utils as utils_module
    
    # Check version compatibility (optional warning)
    version = getattr(agentic_learning, '__version__', 'unknown')
    if version not in ["0.4.3", "0.4.4", "unknown"]:
        print(f"[Warning] Letta patch tested on v0.4.3, you have v{version}", file=sys.stderr)
    
    # Replace the original function with our patched version
    utils_module._save_conversation_turn_async = _patched_save_conversation_turn_async
    
    print("✓ Letta monkey patch applied: provider='letta', model='deepseek/deepseek-v3.2'", file=sys.stderr)


def remove_letta_patch():
    """
    Remove the monkey patch and restore original function.
    
    Useful for testing or cleanup.
    """
    import agentic_learning.interceptors.utils as utils_module
    
    # Restore original function
    utils_module._save_conversation_turn_async = _original_save
    
    print("✓ Letta monkey patch removed", file=sys.stderr)
