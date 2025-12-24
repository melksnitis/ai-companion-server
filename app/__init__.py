"""AI Companion Server Application Package"""

# Override Letta's interceptor system to use only our OpenRouter interceptor
import sys
from app.interceptors.openrouter import OpenRouterInterceptor

def _setup_interceptor():
    """Setup custom interceptor to replace default ones."""
    from agentic_learning.interceptors import registry
    
    # Store original install
    _original_install = registry.install
    
    def _custom_install():
        """Custom install that only installs OpenRouterInterceptor."""
        installed = []
        
        if OpenRouterInterceptor.is_available():
            try:
                interceptor = OpenRouterInterceptor()
                interceptor.install()
                registry._INSTALLED_INTERCEPTORS.append(interceptor)
                installed.append('OpenRouterInterceptor')
                print(f"[App] ✓ Installed OpenRouterInterceptor (provider='openai')", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[App] ✗ Failed: {e}", file=sys.stderr, flush=True)
        
        return installed
    
    # Replace install function
    registry.install = _custom_install
    
    # Also patch in main module
    import agentic_learning.interceptors
    agentic_learning.interceptors.install = _custom_install
    
    print("[App] ✓ Overrode install() for OpenRouterInterceptor only", file=sys.stderr, flush=True)

_setup_interceptor()
