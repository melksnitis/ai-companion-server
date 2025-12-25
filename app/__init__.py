"""AI Companion Server Application Package"""

# Monkey patch learning() to accept interceptor parameter
import sys
from typing import List, Optional, Union

print("[App __init__] Starting app/__init__.py", file=sys.stderr, flush=True)

def _monkey_patch_learning_function():
    """
    Replace learning() with custom version that accepts interceptor_class parameter.
    This allows us to control which interceptor is used per-context.
    """
    try:
        import agentic_learning
        from agentic_learning import core
        from agentic_learning.interceptors import registry
        
        # Store original learning function
        original_learning = core.learning
        
        def custom_learning(
            agent: str = "letta_agent",
            client: Optional[Union["AgenticLearning", "AsyncAgenticLearning"]] = None,
            capture_only: bool = False,
            memory: List[str] = ["human"],
            interceptor_class = None,  # NEW: Allow specifying interceptor class
        ):
            """
            Custom learning() that accepts interceptor_class parameter.
            If interceptor_class is provided, installs only that interceptor.
            Otherwise falls back to default behavior.
            """
            print(f"[CUSTOM LEARNING] ✓ Called! agent={agent}, interceptor_class={interceptor_class}", file=sys.stderr, flush=True)
            print(f"[CUSTOM LEARNING] _INTERCEPTORS_INSTALLED={core._INTERCEPTORS_INSTALLED}", file=sys.stderr, flush=True)
            
            # If specific interceptor requested, install only that one
            if interceptor_class is not None and not core._INTERCEPTORS_INSTALLED:
                print(f"[App] Installing custom interceptor: {interceptor_class.__name__}", file=sys.stderr, flush=True)
                
                if interceptor_class.is_available():
                    interceptor = interceptor_class()
                    interceptor.install()
                    registry._INSTALLED_INTERCEPTORS.append(interceptor)
                    print(f"[App] ✓ Installed {interceptor_class.__name__} (PROVIDER='{interceptor.PROVIDER}')", file=sys.stderr, flush=True)
                
                core._INTERCEPTORS_INSTALLED = True
            
            # Return the original LearningContext
            return core.LearningContext(
                agent=agent,
                client=client,
                capture_only=capture_only,
                memory=memory,
            )
        
        # Replace learning() in both places
        core.learning = custom_learning
        agentic_learning.learning = custom_learning
        
        # Verify the patch worked
        print(f"[App] core.learning is custom: {core.learning is custom_learning}", file=sys.stderr, flush=True)
        print(f"[App] agentic_learning.learning is custom: {agentic_learning.learning is custom_learning}", file=sys.stderr, flush=True)
        print("[App] ✓ Monkey patched learning() to accept interceptor_class", file=sys.stderr, flush=True)
        
        # Patch save functions to force provider='openai'
        from agentic_learning.interceptors import utils
        
        original_save_async = utils._save_conversation_turn_async
        
        async def patched_save_async(provider, model, request_messages, response_dict, register_task=None):
            # Force provider to 'openai' for OpenRouter compatibility
            forced_provider = "openai"
            forced_model = "deepseek-v3"
            print(f"[Save] provider={forced_provider}, model={forced_model}", file=sys.stderr, flush=True)
            
            # Get config and call API directly
            from agentic_learning.core import get_current_config
            config = get_current_config()
            if not config:
                print(f"[Save] No config - skipping", file=sys.stderr, flush=True)
                return None
                
            agent = config.get("agent_name")
            client = config.get("client")
            memory = config.get("memory")
            
            if not client:
                print(f"[Save] No client - skipping", file=sys.stderr, flush=True)
                return None
            
            try:
                import asyncio
                # Try direct API call with timeout
                print(f"[Save] Saving to agent={agent}...", file=sys.stderr, flush=True)
                result = await asyncio.wait_for(
                    client.messages.capture(
                        agent=agent,
                        request_messages=request_messages or [],
                        response_dict=response_dict or {},
                        model=forced_model,
                        provider=forced_provider,
                    ),
                    timeout=5.0
                )
                print(f"[Save] SUCCESS", file=sys.stderr, flush=True)
                return result
            except asyncio.TimeoutError:
                print(f"[Save] TIMEOUT - Letta server not responding", file=sys.stderr, flush=True)
                return None
            except Exception as e:
                print(f"[Save] ERROR: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                return None
        
        utils._save_conversation_turn_async = patched_save_async
        print("[App] ✓ Patched save function to force provider='openai'", file=sys.stderr, flush=True)
        
    except Exception as e:
        print(f"[App] ✗ Setup failed: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)

_monkey_patch_learning_function()
