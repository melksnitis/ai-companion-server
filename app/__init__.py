"""AI Companion Server Application Package"""

# Use ClaudeInterceptor (subprocess) with PROVIDER='openai' for OpenRouter
import sys

def _install_claude_interceptor_with_openai_provider():
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
        
        # Patch extract_model_name to return OpenRouter model format
        original_extract_model = ClaudeInterceptor.extract_model_name
        
        def patched_extract_model(self, response=None, model_self=None):
            return "openai-proxy/deepseek/deepseek-v3.2"
        
        ClaudeInterceptor.extract_model_name = patched_extract_model
        print(f"[App] ✓ Patched ClaudeInterceptor.extract_model_name", file=sys.stderr, flush=True)
        
        # Patch __init__ to set instance PROVIDER
        original_init = ClaudeInterceptor.__init__
        
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.PROVIDER = "openai"
        
        ClaudeInterceptor.__init__ = patched_init
        print(f"[App] ✓ Patched ClaudeInterceptor.__init__", file=sys.stderr, flush=True)
        
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
