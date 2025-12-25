"""AI Companion Server Application Package"""

# Manual interceptor installation to control which interceptor is used
import sys

def _install_openrouter_interceptor_only():
    """
    Manually install only OpenRouterInterceptor and prevent Letta from auto-installing defaults.
    
    This bypasses Letta's _ensure_interceptors_installed() which would install ALL interceptors.
    """
    try:
        from agentic_learning import core
        from agentic_learning.interceptors import registry
        from app.interceptors.openrouter import OpenRouterInterceptor
        
        # Install only our OpenRouterInterceptor
        if OpenRouterInterceptor.is_available():
            interceptor = OpenRouterInterceptor()
            interceptor.install()
            registry._INSTALLED_INTERCEPTORS.append(interceptor)
            print(f"[App] ✓ Installed OpenRouterInterceptor (PROVIDER='openai')", file=sys.stderr, flush=True)
        else:
            print(f"[App] ✗ OpenRouterInterceptor not available", file=sys.stderr, flush=True)
            return
        
        # Mark interceptors as installed to prevent Letta from auto-installing
        core._INTERCEPTORS_INSTALLED = True
        print(f"[App] ✓ Blocked Letta auto-install - using OpenRouterInterceptor only", file=sys.stderr, flush=True)
        
        # Patch save functions to force provider='openai' as extra safety
        from agentic_learning.interceptors import utils
        
        original_save_async = utils._save_conversation_turn_async
        original_save_sync = utils._save_conversation_turn
        
        async def patched_save_async(provider, model, request_messages, response_dict):
            print(f"[Save] provider={provider}, model={model}", file=sys.stderr, flush=True)
            # Force openai provider and openrouter model format
            return await original_save_async("openai", "openai-proxy/deepseek/deepseek-v3.2", request_messages, response_dict)
        
        def patched_save_sync(provider, model, request_messages, response_dict):
            print(f"[Save Sync] provider={provider}, model={model}", file=sys.stderr, flush=True)
            return original_save_sync("openai", "openai-proxy/deepseek/deepseek-v3.2", request_messages, response_dict)
        
        utils._save_conversation_turn_async = patched_save_async
        utils._save_conversation_turn = patched_save_sync
        
        print("[App] ✓ Patched save functions to force provider='openai'", file=sys.stderr, flush=True)
        
    except Exception as e:
        print(f"[App] ✗ Setup failed: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)

_install_openrouter_interceptor_only()
