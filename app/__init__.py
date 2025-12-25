"""AI Companion Server Application Package"""

# Monkey patch to force provider='openai' at the save level + debug interceptor
import sys

def _patch_save_and_interceptor():
    """Patch save functions and add interceptor debugging."""
    try:
        from agentic_learning.interceptors import utils, registry
        from agentic_learning.interceptors.anthropic import AnthropicInterceptor
        
        # Patch AnthropicInterceptor to log when it's called
        original_anthropic_install = AnthropicInterceptor.install
        
        def patched_install(self):
            print(f"[Interceptor] AnthropicInterceptor.install() called", file=sys.stderr, flush=True)
            result = original_anthropic_install(self)
            print(f"[Interceptor] AnthropicInterceptor installed, PROVIDER={self.PROVIDER}", file=sys.stderr, flush=True)
            return result
        
        AnthropicInterceptor.install = patched_install
        
        # Patch the intercept_async method to log when calls are intercepted
        from agentic_learning.interceptors.base import BaseAPIInterceptor
        original_intercept_async = BaseAPIInterceptor.intercept_async
        
        def patched_intercept_async(self, original_method):
            print(f"[Interceptor] intercept_async called for {self.__class__.__name__}", file=sys.stderr, flush=True)
            wrapper = original_intercept_async(self, original_method)
            
            async def logged_wrapper(*args, **kwargs):
                print(f"[Interceptor] SDK call intercepted by {self.__class__.__name__}", file=sys.stderr, flush=True)
                return await wrapper(*args, **kwargs)
            
            return logged_wrapper
        
        BaseAPIInterceptor.intercept_async = patched_intercept_async
        
        # Store original save functions
        original_save_async = utils._save_conversation_turn_async
        original_save_sync = utils._save_conversation_turn
        
        async def patched_save_async(provider, model, request_messages, response_dict):
            """Force provider='openai' and model to OpenRouter format."""
            print(f"[Save] CALLED: provider={provider}, model={model}", file=sys.stderr, flush=True)
            forced_provider = "openai"
            forced_model = "openai-proxy/deepseek/deepseek-v3.2"
            print(f"[Save] FORCING: provider={forced_provider}, model={forced_model}", file=sys.stderr, flush=True)
            return await original_save_async(forced_provider, forced_model, request_messages, response_dict)
        
        def patched_save_sync(provider, model, request_messages, response_dict):
            """Force provider='openai' and model to OpenRouter format."""
            print(f"[Save Sync] CALLED: provider={provider}, model={model}", file=sys.stderr, flush=True)
            forced_provider = "openai"
            forced_model = "openai-proxy/deepseek/deepseek-v3.2"
            print(f"[Save Sync] FORCING: provider={forced_provider}, model={forced_model}", file=sys.stderr, flush=True)
            return original_save_sync(forced_provider, forced_model, request_messages, response_dict)
        
        utils._save_conversation_turn_async = patched_save_async
        utils._save_conversation_turn = patched_save_sync
        
        print("[App] ✓ Patched save functions + interceptor logging", file=sys.stderr, flush=True)
        
    except Exception as e:
        print(f"[App] ✗ Failed to patch: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)

_patch_save_and_interceptor()
