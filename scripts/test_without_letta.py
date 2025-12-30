#!/usr/bin/env python3
"""
Test script WITHOUT Letta Learning SDK wrapper.

Run this to verify that the raw Claude SDK path uses the correct model.
Compare OpenRouter activity CSV after running this vs test_with_letta.py.
"""

import asyncio
import os
import sys
from pathlib import Path

# Capture command-line env vars BEFORE load_dotenv overwrites them
_CLI_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

# Configure OpenRouter API (same as AgentService does)
# Use CLI override if provided, otherwise default to OpenRouter
os.environ["ANTHROPIC_BASE_URL"] = _CLI_BASE_URL or "https://openrouter.ai/api"
os.environ["ANTHROPIC_AUTH_TOKEN"] = os.getenv("OPENROUTER_API_KEY", "")
os.environ["ANTHROPIC_API_KEY"] = ""  # Must be empty to prevent conflicts


async def main():
    model_id = os.getenv("OPENROUTER_MODEL_ID", "xiaomi/mimo-v2-flash:free")
    print(f"[TEST WITHOUT LETTA] Using model: {model_id}")
    print(f"[TEST WITHOUT LETTA] ANTHROPIC_BASE_URL: {os.environ.get('ANTHROPIC_BASE_URL')}")
    print(f"[TEST WITHOUT LETTA] ANTHROPIC_AUTH_TOKEN set: {bool(os.environ.get('ANTHROPIC_AUTH_TOKEN'))}")
    print(f"[TEST WITHOUT LETTA] OPENROUTER_MODEL_ID env: {os.getenv('OPENROUTER_MODEL_ID')}")
    print(f"[TEST WITHOUT LETTA] ANTHROPIC_DEFAULT_SONNET_MODEL env: {os.getenv('ANTHROPIC_DEFAULT_SONNET_MODEL')}")
    
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Bash"],
        model=model_id,
        cli_path="/usr/local/Cellar/node/23.6.1/bin/claude"
    )
    
    print(f"[TEST WITHOUT LETTA] ClaudeAgentOptions.model = {options.model}")
    print("[TEST WITHOUT LETTA] Starting WITHOUT learning() context...")
    
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt="Run: echo 'test without letta'")
        async for msg in client.receive_response():
            msg_type = type(msg).__name__
            print(f"[TEST WITHOUT LETTA] Received: {msg_type}")
            if msg_type == 'AssistantMessage':
                for block in msg.content:
                    if hasattr(block, 'text'):
                        print(f"[TEST WITHOUT LETTA] Response: {block.text[:200]}")

    print("[TEST WITHOUT LETTA] Done. Check OpenRouter activity CSV for this request.")


if __name__ == "__main__":
    asyncio.run(main())
