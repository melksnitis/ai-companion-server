"""AI Companion Server Application Package"""

# Register custom OpenRouter interceptor with Letta
# We need to remove the default AnthropicInterceptor to prevent conflicts
import sys
from agentic_learning.interceptors import register_interceptor, _INTERCEPTOR_CLASSES
from agentic_learning.interceptors.anthropic import AnthropicInterceptor
from app.interceptors.openrouter import OpenRouterInterceptor

# Remove default AnthropicInterceptor to prevent it from overwriting our patches
if AnthropicInterceptor in _INTERCEPTOR_CLASSES:
    _INTERCEPTOR_CLASSES.remove(AnthropicInterceptor)
    print("[App] ✓ Removed default AnthropicInterceptor", file=sys.stderr, flush=True)

# Register our custom OpenRouter interceptor
register_interceptor(OpenRouterInterceptor)
print("[App] ✓ Registered OpenRouterInterceptor with Letta", file=sys.stderr, flush=True)
