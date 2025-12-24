"""AI Companion Server Application Package"""

# Override Letta's interceptor system to use only our OpenRouter interceptor
import sys
from agentic_learning.interceptors import registry
from app.interceptors.openrouter import OpenRouterInterceptor

# Store original install function
_original_install = registry.install

def _custom_install():
    """Custom install that only installs OpenRouterInterceptor."""
    installed = []
    
    # Only install our OpenRouter interceptor
    if OpenRouterInterceptor.is_available():
        try:
            interceptor = OpenRouterInterceptor()
            interceptor.install()
            registry._INSTALLED_INTERCEPTORS.append(interceptor)
            installed.append('OpenRouterInterceptor')
            print(f"[App] ✓ Installed OpenRouterInterceptor (provider='openai')", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[App] ✗ Failed to install OpenRouterInterceptor: {e}", file=sys.stderr, flush=True)
    
    return installed

# Replace Letta's install function with ours
registry.install = _custom_install

# Also patch it in the main module so learning() uses our version
import agentic_learning.interceptors
agentic_learning.interceptors.install = _custom_install

print("[App] ✓ Overrode Letta's install() to use OpenRouterInterceptor only", file=sys.stderr, flush=True)
