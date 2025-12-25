"""
Custom OpenRouter Interceptor for Letta Learning SDK.
Extends ClaudeInterceptor (subprocess-based) with provider='openai' for OpenRouter.
"""

import sys
from typing import Any, Dict, List
from agentic_learning.interceptors.claude import ClaudeInterceptor


class OpenRouterInterceptor(ClaudeInterceptor):
    """
    Interceptor for OpenRouter API calls using Anthropic SDK.
    Uses provider='openai' since OpenRouter is OpenAI-compatible.
    """
    
    PROVIDER = "openai"
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if anthropic SDK is available."""
        try:
            import anthropic
            return True
        except ImportError:
            return False
    
    def install(self):
        """Install interceptor by patching Anthropic SDK methods."""
        try:
            from anthropic.resources.messages import Messages, AsyncMessages
        except ImportError:
            print("[OpenRouterInterceptor] ⚠️ Anthropic SDK not available", file=sys.stderr, flush=True)
            return
        
        # Store original methods
        self._original_methods['messages_create'] = Messages.create
        self._original_methods['async_messages_create'] = AsyncMessages.create
        
        print(f"[OpenRouterInterceptor] Patching AsyncMessages.create...", file=sys.stderr, flush=True)
        
        # Patch with wrapped versions
        Messages.create = self.intercept(self._original_methods['messages_create'])
        AsyncMessages.create = self.intercept_async(self._original_methods['async_messages_create'])
        
        print(f"[OpenRouterInterceptor] ✓ Patched - PROVIDER='{self.PROVIDER}'", file=sys.stderr, flush=True)
        
        # Add debug wrapper to verify calls are being intercepted
        original_async_create = AsyncMessages.create
        
        async def debug_wrapper(*args, **kwargs):
            print(f"[OpenRouterInterceptor] 🎯 AsyncMessages.create CALLED!", file=sys.stderr, flush=True)
            result = await original_async_create(*args, **kwargs)
            print(f"[OpenRouterInterceptor] 🎯 AsyncMessages.create RETURNED", file=sys.stderr, flush=True)
            return result
        
        AsyncMessages.create = debug_wrapper
        print("[OpenRouterInterceptor] ✓ Added debug wrapper", file=sys.stderr, flush=True)
    
    def uninstall(self):
        """Uninstall interceptor and restore original methods."""
        try:
            from anthropic.resources.messages import Messages, AsyncMessages
        except ImportError:
            return
        
        if 'messages_create' in self._original_methods:
            Messages.create = self._original_methods['messages_create']
        if 'async_messages_create' in self._original_methods:
            AsyncMessages.create = self._original_methods['async_messages_create']
    
    def extract_user_messages(self, *args, **kwargs) -> str:
        """Extract user message from messages.create arguments."""
        messages = kwargs.get('messages', [])
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        if not user_messages:
            return ""
        # Combine all user message content
        user_content = []
        for msg in user_messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                user_content.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        user_content.append(block.get('text', ''))
        return '\n'.join(user_content)
    
    def build_request_messages(self, user_message: str) -> List[Dict[str, Any]]:
        """Build request messages for Letta API."""
        if not user_message:
            return []
        return [{'role': 'user', 'content': user_message}]
    
    def build_response_dict(self, response: Any) -> Dict[str, Any]:
        """Build response dictionary from Anthropic SDK response."""
        if not response:
            return {}
        
        if hasattr(response, 'content') and response.content:
            first_block = response.content[0]
            if hasattr(first_block, 'text'):
                return {
                    'role': 'assistant',
                    'content': first_block.text
                }
        
        return {}
    
    def extract_model_name(self, response: Any = None, model_self: Any = None) -> str:
        """Extract model name - returns OpenRouter model format."""
        return "openai-proxy/deepseek/deepseek-v3.2"
    
    def _build_response_from_chunks(self, chunks: list) -> Any:
        """Build complete response from streaming chunks."""
        if not chunks:
            return None
        
        text_content = []
        for chunk in chunks:
            if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text'):
                text_content.append(chunk.delta.text)
        
        # Create mock response object
        class MockResponse:
            def __init__(self, text):
                self.content = [MockContent(text)]
        
        class MockContent:
            def __init__(self, text):
                self.text = text
        
        return MockResponse(''.join(text_content))
