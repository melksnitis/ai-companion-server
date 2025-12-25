"""AI Companion Server Application Package"""

# Monkey patch learning() to accept interceptor parameter
import sys
from typing import List, Optional, Union

def _monkey_patch_learning_function():
    """
    Replace learning() with custom version that accepts interceptor_class parameter.
    This allows us to control which interceptor is used per-context.
    """
    try:
        import agentic_learning
        from agentic_learning import core
        from agentic_learning.interceptors import registry
        from agentic_learning.interceptors.claude import ClaudeInterceptor
        
        # Patch ClaudeInterceptor to use PROVIDER='openai'
        ClaudeInterceptor.PROVIDER = "openai"
        original_init = ClaudeInterceptor.__init__
        
        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.PROVIDER = "openai"
        
        ClaudeInterceptor.__init__ = patched_init
        print(f"[App] ✓ Patched ClaudeInterceptor.PROVIDER = 'openai'", file=sys.stderr, flush=True)
        
        # Store original learning function
        original_learning = core.learning
        
        def custom_learning(
            agent: str = "letta_agent",
            client: Optional[Union["AgenticLearning", "AsyncAgenticLearning"]] = None,
            capture_only: bool = False,
            memory: List[str] = ["human"],
            interceptor_class = None,  # NEW: Allow specifying interceptor class
        ):
            """
            Custom learning() that accepts interceptor_class parameter.
            If interceptor_class is provided, installs only that interceptor.
            Otherwise falls back to default behavior.
            """
            # If specific interceptor requested, install only that one
            if interceptor_class is not None and not core._INTERCEPTORS_INSTALLED:
                print(f"[App] Installing custom interceptor: {interceptor_class.__name__}", file=sys.stderr, flush=True)
                
                if interceptor_class.is_available():
                    interceptor = interceptor_class()
                    interceptor.install()
                    registry._INSTALLED_INTERCEPTORS.append(interceptor)
                    print(f"[App] ✓ Installed {interceptor_class.__name__} (PROVIDER='{interceptor.PROVIDER}')", file=sys.stderr, flush=True)
                
                core._INTERCEPTORS_INSTALLED = True
            
            # Return the original LearningContext
            return core.LearningContext(
                agent=agent,
                client=client,
                capture_only=capture_only,
                memory=memory,
            )
        
        # Replace learning() in both places
        core.learning = custom_learning
        agentic_learning.learning = custom_learning
        
        print("[App] ✓ Monkey patched learning() to accept interceptor_class", file=sys.stderr, flush=True)
        
        # Patch save functions to force provider='openai'
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

_monkey_patch_learning_function()
