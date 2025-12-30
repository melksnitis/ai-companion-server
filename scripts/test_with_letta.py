#!/usr/bin/env python3
"""
Test script WITH Letta Learning SDK wrapper.

Run this to verify that the Letta interceptor path uses the correct model.
Compare OpenRouter activity CSV after running this vs test_without_letta.py.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from agentic_learning import learning
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

# Configure OpenRouter API (same as AgentService does)
os.environ["ANTHROPIC_BASE_URL"] = "https://openrouter.ai/api"
os.environ["ANTHROPIC_AUTH_TOKEN"] = os.getenv("OPENROUTER_API_KEY", "")
os.environ["ANTHROPIC_API_KEY"] = ""  # Must be empty to prevent conflicts


async def main():
    model_id = os.getenv("OPENROUTER_MODEL_ID", "xiaomi/mimo-v2-flash:free")
    print(f"[TEST WITH LETTA] Using model: {model_id}")
    print(f"[TEST WITH LETTA] ANTHROPIC_BASE_URL: {os.environ.get('ANTHROPIC_BASE_URL')}")
    print(f"[TEST WITH LETTA] ANTHROPIC_AUTH_TOKEN set: {bool(os.environ.get('ANTHROPIC_AUTH_TOKEN'))}")
    print(f"[TEST WITH LETTA] OPENROUTER_MODEL_ID env: {os.getenv('OPENROUTER_MODEL_ID')}")
    print(f"[TEST WITH LETTA] ANTHROPIC_DEFAULT_SONNET_MODEL env: {os.getenv('ANTHROPIC_DEFAULT_SONNET_MODEL')}")
    
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Bash"],
        model=model_id,
        cli_path="/usr/local/Cellar/node/23.6.1/bin/claude"
    )
    
    print(f"[TEST WITH LETTA] ClaudeAgentOptions.model = {options.model}")
    print("[TEST WITH LETTA] Starting with learning() context...")
    
    async with learning(agent="debug-test-with-letta"):
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt="Run: echo 'test with letta'")
            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                print(f"[TEST WITH LETTA] Received: {msg_type}")
                if msg_type == 'AssistantMessage':
                    for block in msg.content:
                        if hasattr(block, 'text'):
                            print(f"[TEST WITH LETTA] Response: {block.text[:200]}")

    print("[TEST WITH LETTA] Done. Check OpenRouter activity CSV for this request.")


if __name__ == "__main__":
    asyncio.run(main())
