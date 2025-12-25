"""AI Companion Server Application Package"""

# Monkey patch to force provider='openai' at the save level
import sys

def _patch_save_conversation():
    """Patch _save_conversation_turn_async to force provider='openai'."""
    try:
        from agentic_learning.interceptors import utils
        
        # Store original
        original_save_async = utils._save_conversation_turn_async
        original_save_sync = utils._save_conversation_turn
        
        async def patched_save_async(provider, model, request_messages, response_dict):
            """Force provider='openai' and model to OpenRouter format."""
            print(f"[Save Debug] Original: provider={provider}, model={model}", file=sys.stderr, flush=True)
            forced_provider = "openai"
            forced_model = "openai-proxy/deepseek/deepseek-v3.2"
            print(f"[Save Debug] Forced: provider={forced_provider}, model={forced_model}", file=sys.stderr, flush=True)
            return await original_save_async(forced_provider, forced_model, request_messages, response_dict)
        
        def patched_save_sync(provider, model, request_messages, response_dict):
            """Force provider='openai' and model to OpenRouter format."""
            print(f"[Save Debug] Sync Original: provider={provider}, model={model}", file=sys.stderr, flush=True)
            forced_provider = "openai"
            forced_model = "openai-proxy/deepseek/deepseek-v3.2"
            print(f"[Save Debug] Sync Forced: provider={forced_provider}, model={forced_model}", file=sys.stderr, flush=True)
            return original_save_sync(forced_provider, forced_model, request_messages, response_dict)
        
        utils._save_conversation_turn_async = patched_save_async
        utils._save_conversation_turn = patched_save_sync
        
        print("[App] ✓ Patched _save_conversation_turn to force provider='openai'", file=sys.stderr, flush=True)
        
    except Exception as e:
        print(f"[App] ✗ Failed to patch save functions: {e}", file=sys.stderr, flush=True)

_patch_save_conversation()
