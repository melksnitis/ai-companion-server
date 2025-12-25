"""AI Companion Server Application Package"""

# Monkey patch learning() to accept interceptor parameter
import sys
from typing import List, Optional, Union

def _monkey_patch_learning_function():
    """
    Install ClaudeInterceptor (subprocess-based) but patch it to use PROVIDER='openai'.
    
    Claude Agent SDK uses SubprocessCLITransport (spawns claude CLI subprocess),
    NOT the Anthropic SDK, so we need ClaudeInterceptor instead of AnthropicInterceptor.
    """
    try:
        from agentic_learning import core
        from agentic_learning.interceptors import registry
        from agentic_learning.interceptors.claude import ClaudeInterceptor
        
        # Patch ClaudeInterceptor to use PROVIDER='openai' for OpenRouter
        ClaudeInterceptor.PROVIDER = "openai"
        print(f"[App] ✓ Patched ClaudeInterceptor.PROVIDER = 'openai'", file=sys.stderr, flush=True)
        
        # Patch __init__ to set instance PROVIDER
        original_init = ClaudeInterceptor.__init__
        
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.PROVIDER = "openai"
        
        ClaudeInterceptor.__init__ = patched_init
        print(f"[App] ✓ Patched ClaudeInterceptor.__init__", file=sys.stderr, flush=True)
        
        # Patch _wrap_message_iterator to add debug logging
        original_wrap = ClaudeInterceptor._wrap_message_iterator
        
        def debug_wrap(self, original_iterator, config):
            print(f"[Claude] _wrap_message_iterator called", file=sys.stderr, flush=True)
            result = original_wrap(self, original_iterator, config)
            print(f"[Claude] _wrap_message_iterator returning wrapped iterator", file=sys.stderr, flush=True)
            return result
        
        ClaudeInterceptor._wrap_message_iterator = debug_wrap
        
        # Install ClaudeInterceptor
        if ClaudeInterceptor.is_available():
            interceptor = ClaudeInterceptor()
            interceptor.install()
            registry._INSTALLED_INTERCEPTORS.append(interceptor)
            print(f"[App] ✓ Installed ClaudeInterceptor (PROVIDER='openai')", file=sys.stderr, flush=True)
        else:
            print(f"[App] ✗ ClaudeInterceptor not available", file=sys.stderr, flush=True)
            return
        
        # Block auto-install
        core._INTERCEPTORS_INSTALLED = True
        print(f"[App] ✓ Blocked Letta auto-install", file=sys.stderr, flush=True)
        
        # Patch save functions as extra safety
        from agentic_learning.interceptors import utils
        
        original_save_async = utils._save_conversation_turn_async
        
        async def patched_save_async(provider, model, request_messages, response_dict):
            print(f"[Save] provider={provider}, model={model}", file=sys.stderr, flush=True)
            return await original_save_async("openai", "openai-proxy/deepseek/deepseek-v3.2", request_messages, response_dict)
        
        utils._save_conversation_turn_async = patched_save_async
        print("[App] ✓ Patched save function to force provider='openai'", file=sys.stderr, flush=True)
        
    except Exception as e:
        print(f"[App] ✗ Setup failed: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)

_install_claude_interceptor_with_openai_provider()
