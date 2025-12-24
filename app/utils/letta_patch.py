"""
Monkey patch for Letta Learning SDK to support DeepSeek via OpenRouter.
Uses wrapt's post import hooks to patch modules BEFORE caching occurs.
"""

import sys
from typing import Dict, List
from agentic_learning.core import get_current_config

_original_save = None


async def _patched_save_conversation_turn_async(
    provider: str,
    model: str,
    request_messages: List[dict] = None,
    response_dict: Dict[str, str] = None,
    register_task: bool = False,
):
    """Patched version that overrides provider to 'letta'."""
    patched_provider = "letta"
    patched_model = model if model != "claude" else "deepseek/deepseek-v3.2"
    
    print(f"[PATCH DEBUG] Called with provider='{provider}' -> '{patched_provider}'", file=sys.stderr)
    
    config = get_current_config()
    if not config:
        return
    
    agent = config["agent_name"]
    client = config["client"]
    memory = config.get("memory")
    
    if not client:
        return
    
    async def save_task():
        try:
            is_async = hasattr(client, '__class__') and 'Async' in client.__class__.__name__
            
            if is_async:
                agent_state = await client.agents.retrieve(agent=agent)
                if not agent_state:
                    agent_state = await client.agents.create(agent=agent, memory=memory)
                
                print(f"[PATCH DEBUG] Calling capture with provider='{patched_provider}'", file=sys.stderr)
                result = await client.messages.capture(
                    agent=agent,
                    request_messages=request_messages or [],
                    response_dict=response_dict or {},
                    model=patched_model,
                    provider=patched_provider,
                )
                print(f"[PATCH DEBUG] Capture succeeded!", file=sys.stderr)
                return result
            else:
                import asyncio
                loop = asyncio.get_event_loop()
                
                agent_state = await loop.run_in_executor(
                    None,
                    lambda: client.agents.retrieve(agent=agent)
                )
                if not agent_state:
                    agent_state = await loop.run_in_executor(
                        None,
                        lambda: client.agents.create(agent=agent, memory=memory)
                    )
                
                return await loop.run_in_executor(
                    None,
                    lambda: client.messages.capture(
                        agent=agent,
                        request_messages=request_messages or [],
                        response_dict=response_dict or {},
                        model=patched_model,
                        provider=patched_provider,
                    )
                )
        
        except Exception as e:
            print(f"[PATCH DEBUG] Exception: {e}", file=sys.stderr)
            print(f"[Warning] Failed to save conversation turn: {e}", file=sys.stderr)
    
    if register_task:
        import asyncio
        task = asyncio.create_task(save_task())
        config.get("pending_tasks", []).append(task)
    else:
        await save_task()


def _patch_utils_module(utils_module):
    """Callback: Patch utils when imported."""
    global _original_save
    _original_save = utils_module._save_conversation_turn_async
    utils_module._save_conversation_turn_async = _patched_save_conversation_turn_async
    print(f"[PATCH] ✓ Patched utils._save_conversation_turn_async", file=sys.stderr)


def apply_letta_patch():
    """Apply patch using wrapt's post import hooks."""
    try:
        from wrapt import register_post_import_hook
    except ImportError:
        print("[PATCH] ❌ wrapt not installed", file=sys.stderr)
        return
    
    # Patch utils module
    register_post_import_hook(_patch_utils_module, 'agentic_learning.interceptors.utils')
    
    # CRITICAL: Patch the install() function to re-apply our patches AFTER it runs
    def patch_interceptors_init(module):
        original_install = module.install
        
        def patched_install():
            # Call original install
            original_install()
            print("[PATCH] Interceptors installed by Letta, re-applying patches...", file=sys.stderr)
            
            # Re-apply ALL our patches AFTER Letta's install
            try:
                # Patch utils
                from agentic_learning.interceptors import utils as utils_module
                global _original_save
                _original_save = utils_module._save_conversation_turn_async
                utils_module._save_conversation_turn_async = _patched_save_conversation_turn_async
                print("[PATCH] ✓ Re-patched utils", file=sys.stderr)
                
                # Patch BaseAPIInterceptor
                from agentic_learning.interceptors import base as base_module
                patch_base_interceptor(base_module)
                
                # Patch interceptor instances
                from agentic_learning.interceptors.claude import ClaudeInterceptor
                from agentic_learning.interceptors.anthropic import AnthropicInterceptor
                ClaudeInterceptor.PROVIDER = "letta"
                AnthropicInterceptor.PROVIDER = "letta"
                print("[PATCH] ✓ Re-patched interceptor PROVIDER constants", file=sys.stderr)
            except Exception as e:
                print(f"[PATCH] ⚠️ Error re-applying patches: {e}", file=sys.stderr)
        
        module.install = patched_install
        print("[PATCH] ✓ Wrapped interceptors.install()", file=sys.stderr)
    
    register_post_import_hook(patch_interceptors_init, 'agentic_learning.interceptors')
    
    # Patch BaseAPIInterceptor on import
    def patch_base_interceptor(module):
        # Patch BOTH intercept (sync) and intercept_async methods
        
        # Patch intercept_async
        original_intercept_async = module.BaseAPIInterceptor.intercept_async
        
        def patched_intercept_async(self, original_method):
            import functools
            interceptor = self
            
            @functools.wraps(original_method)
            async def wrapper(self_arg, *args, **kwargs):
                from agentic_learning.core import get_current_config
                
                config = get_current_config()
                if not config:
                    return await original_method(self_arg, *args, **kwargs)
                
                user_message = interceptor.extract_user_messages(*args, **kwargs)
                kwargs = await interceptor._retrieve_and_inject_memory_async(config, kwargs)
                is_streaming = kwargs.get('stream', False)
                response = await original_method(self_arg, *args, **kwargs)
                
                if is_streaming:
                    response._learning_user_message = user_message
                    response._learning_model_name = kwargs.get('model', 'unknown')
                    return interceptor.extract_assistant_message_streaming_async(response)
                else:
                    model_name = interceptor.extract_model_name(response=response, model_self=self_arg)
                    response_dict = interceptor.build_response_dict(response=response)
                    
                    if response_dict.get("content"):
                        from agentic_learning.interceptors.utils import _save_conversation_turn_async
                        try:
                            await _save_conversation_turn_async(
                                provider="letta",
                                model=model_name,
                                request_messages=interceptor.build_request_messages(user_message),
                                response_dict=response_dict
                            )
                        except Exception as e:
                            import sys
                            print(f"[Warning] Failed to save conversation: {e}", file=sys.stderr)
                    
                    return response
            
            return wrapper
        
        # Patch intercept (sync)
        original_intercept = module.BaseAPIInterceptor.intercept
        
        def patched_intercept(self, original_method):
            import functools
            interceptor = self
            
            @functools.wraps(original_method)
            def wrapper(self_arg, *args, **kwargs):
                from agentic_learning.core import get_current_config
                
                config = get_current_config()
                if not config:
                    return original_method(self_arg, *args, **kwargs)
                
                user_message = interceptor.extract_user_messages(*args, **kwargs)
                kwargs = interceptor._retrieve_and_inject_memory(config, kwargs)
                is_streaming = kwargs.get('stream', False)
                response = original_method(self_arg, *args, **kwargs)
                
                if is_streaming:
                    response._learning_user_message = user_message
                    response._learning_model_name = kwargs.get('model', 'unknown')
                    return interceptor.extract_assistant_message_streaming(response)
                else:
                    model_name = interceptor.extract_model_name(response=response, model_self=self_arg)
                    response_dict = interceptor.build_response_dict(response=response)
                    
                    if response_dict.get("content"):
                        from agentic_learning.interceptors.utils import _save_conversation_turn
                        try:
                            _save_conversation_turn(
                                provider="letta",
                                model=model_name,
                                request_messages=interceptor.build_request_messages(user_message),
                                response_dict=response_dict
                            )
                        except Exception as e:
                            import sys
                            print(f"[Warning] Failed to save conversation: {e}", file=sys.stderr)
                    
                    return response
            
            return wrapper
        
        module.BaseAPIInterceptor.intercept = patched_intercept
        module.BaseAPIInterceptor.intercept_async = patched_intercept_async
        print(f"[PATCH] ✓ Patched BaseAPIInterceptor.intercept (sync + async)", file=sys.stderr)
    
    # Patch interceptors - wrap __init__ to set instance PROVIDER
    def patch_claude(module):
        original_init = module.ClaudeInterceptor.__init__
        
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.PROVIDER = "letta"
        
        module.ClaudeInterceptor.__init__ = patched_init
        module.ClaudeInterceptor.PROVIDER = "letta"
        print(f"[PATCH] ✓ Patched ClaudeInterceptor (class + instances)", file=sys.stderr)
    
    def patch_anthropic(module):
        original_init = module.AnthropicInterceptor.__init__
        
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.PROVIDER = "letta"
        
        module.AnthropicInterceptor.__init__ = patched_init
        module.AnthropicInterceptor.PROVIDER = "letta"
        print(f"[PATCH] ✓ Patched AnthropicInterceptor (class + instances)", file=sys.stderr)
    
    register_post_import_hook(patch_base_interceptor, 'agentic_learning.interceptors.base')
    register_post_import_hook(patch_claude, 'agentic_learning.interceptors.claude')
    register_post_import_hook(patch_anthropic, 'agentic_learning.interceptors.anthropic')
    
    print("✓ Letta post import hooks registered: provider='letta'", file=sys.stderr)


def remove_letta_patch():
    """Remove patch and restore original."""
    global _original_save
    if _original_save:
        import agentic_learning.interceptors.utils as utils_module
        utils_module._save_conversation_turn_async = _original_save
        print("✓ Letta monkey patch removed", file=sys.stderr)
