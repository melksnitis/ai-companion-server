"""AI Companion Server Application Package"""

# Monkey patch AnthropicInterceptor to use provider='openai'
import sys

def _patch_anthropic_interceptor():
    """Patch AnthropicInterceptor.PROVIDER to 'openai' for OpenRouter compatibility."""
    try:
        from agentic_learning.interceptors.anthropic import AnthropicInterceptor
        
        # Patch the class attribute
        AnthropicInterceptor.PROVIDER = "openai"
        
        # Also patch the instance creation to ensure all instances use openai
        original_init = AnthropicInterceptor.__init__
        
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.PROVIDER = "openai"
        
        AnthropicInterceptor.__init__ = patched_init
        
        # Override extract_model_name to return OpenRouter model format
        def patched_extract_model_name(self, response=None, model_self=None):
            return "openai-proxy/deepseek/deepseek-v3.2"
        
        AnthropicInterceptor.extract_model_name = patched_extract_model_name
        
        print("[App] ✓ Patched AnthropicInterceptor: PROVIDER='openai', model='openai-proxy/deepseek/deepseek-v3.2'", file=sys.stderr, flush=True)
        
    except Exception as e:
        print(f"[App] ✗ Failed to patch AnthropicInterceptor: {e}", file=sys.stderr, flush=True)

_patch_anthropic_interceptor()
