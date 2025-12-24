"""AI Companion Server Application Package"""

# Register custom OpenRouter interceptor with Letta
from agentic_learning.interceptors import register_interceptor
from app.interceptors.openrouter import OpenRouterInterceptor

register_interceptor(OpenRouterInterceptor)
print("[App] ✓ Registered OpenRouterInterceptor with Letta", flush=True)
