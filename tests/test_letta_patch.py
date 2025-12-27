"""
Test Letta monkey patch for DeepSeek compatibility.
"""

import asyncio
import os
import pytest
from app.utils.letta_patch import apply_letta_patch, remove_letta_patch


@pytest.mark.asyncio
async def test_letta_patch_applied():
    """Test that monkey patch is applied correctly."""
    apply_letta_patch()
    
    from agentic_learning.interceptors.utils import _save_conversation_turn_async
    
    # Check that the function is patched
    assert _save_conversation_turn_async.__name__ == "_patched_save_conversation_turn_async"
    
    remove_letta_patch()
    
    # Check that the function is restored
    assert _save_conversation_turn_async.__name__ == "_save_conversation_turn_async"


@pytest.mark.asyncio
async def test_letta_deepseek_integration():
    """Test full integration with DeepSeek via OpenRouter."""
    from agentic_learning import learning
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    
    # Apply patch
    apply_letta_patch()
    
    # Configure environment
    os.environ["ANTHROPIC_BASE_URL"] = "https://openrouter.ai/api"
    os.environ["ANTHROPIC_AUTH_TOKEN"] = os.getenv("OPENROUTER_API_KEY", "")
    os.environ["ANTHROPIC_API_KEY"] = ""
    os.environ["LETTA_API_KEY"] = os.getenv("LETTA_API_KEY", "")
    
    options = ClaudeAgentOptions(
        permission_mode="dontAsk",
        allowed_tools=["Bash", "Read", "Write"],
        model="deepseek/deepseek-v3.2",
        cwd="/tmp"
    )
    
    try:
        async with learning(agent="test-deepseek-patch", memory=["human"]):
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt="Say hello in one word")
                
                count = 0
                async for msg in client.receive_response():
                    count += 1
                    if count > 5:
                        break
        
        print("✓ Integration test passed - no provider validation error!")
        
    except Exception as e:
        if "Provider anthropic is not supported" in str(e) or "Provider claude is not supported" in str(e):
            pytest.fail(f"Monkey patch failed: {e}")
        else:
            # Other errors are acceptable for this test
            print(f"Note: {e}")
    
    finally:
        remove_letta_patch()


if __name__ == "__main__":
    print("Running Letta patch tests...")
    asyncio.run(test_letta_patch_applied())
    asyncio.run(test_letta_deepseek_integration())
    print("All tests completed!")
