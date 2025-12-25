"""
Custom OpenRouter Interceptor for Letta Learning SDK.
Extends ClaudeInterceptor (subprocess-based) with provider='openai' for OpenRouter.
"""

import sys
from agentic_learning.interceptors.claude import ClaudeInterceptor


class OpenRouterInterceptor(ClaudeInterceptor):
    """
    Interceptor for OpenRouter via Claude Agent SDK (subprocess).
    Extends ClaudeInterceptor but uses provider='openai' for OpenRouter compatibility.
    """
    
    # Override to use 'openai' instead of 'claude'
    PROVIDER = "openai"
    
    def __init__(self):
        """Initialize with PROVIDER='openai'."""
        super().__init__()
        self.PROVIDER = "openai"
        print(f"[OpenRouterInterceptor] Initialized with PROVIDER='{self.PROVIDER}'", file=sys.stderr, flush=True)
