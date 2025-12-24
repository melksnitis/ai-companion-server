"""
Simplified Agent Service using Claude Agent SDK with OpenRouter
Direct connection to OpenRouter API (no local router needed)
Follows: https://openrouter.ai/docs/guides/guides/claude-code-integration
"""

import os
from typing import AsyncGenerator, Optional, List, Dict, Any
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock

from app.config import settings
from app.models.schemas import ChatStreamEvent, ToolCall


class AgentService:
    """Simplified agent service using Claude Agent SDK with OpenRouter.
    
    Connects directly to OpenRouter's Anthropic-compatible API.
    OpenRouter handles model routing and provides access to DeepSeek and other models.
    """
    
    def __init__(self):
        # Configure Claude Agent SDK to use OpenRouter directly
        # Following OpenRouter's official guide: https://openrouter.ai/docs/guides/guides/claude-code-integration
        os.environ["ANTHROPIC_BASE_URL"] = "https://openrouter.ai/api"
        os.environ["ANTHROPIC_AUTH_TOKEN"] = settings.openrouter_api_key
        os.environ["ANTHROPIC_API_KEY"] = ""  # Must be explicitly empty to prevent conflicts
    
    def _get_agent_options(self) -> ClaudeAgentOptions:
        """Configure Claude Agent SDK options with tools.
        
        Model selection is handled by OpenRouter.
        Uses DeepSeek v3.2 by default, can be overridden with ANTHROPIC_DEFAULT_SONNET_MODEL env var.
        Workspace is set to /app/workspace for file operations.
        """
        return ClaudeAgentOptions(
            permission_mode="dontAsk",
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Search"],
            model="deepseek/deepseek-v3.2",  # Use DeepSeek v3.2 via OpenRouter (supports tool use)
            cwd="/app/workspace",  # Set working directory for file operations
        )
    
    async def stream_chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        memory_labels: Optional[List[str]] = None,
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """
        Stream a chat response using Claude Agent SDK.
        
        Args:
            message: User message to send
            conversation_id: Optional conversation ID for tracking
            memory_labels: Optional (unused - kept for API compatibility)
        """
        agent_id = conversation_id or "default-agent"
        
        options = self._get_agent_options()
        
        yield ChatStreamEvent(
            event_type="thinking_start",
            data={"message": "Thinking..."}
        )
        
        try:
            async with ClaudeSDKClient(options=options) as client:
                yield ChatStreamEvent(
                    event_type="thinking_stop",
                    data={}
                )
                
                yield ChatStreamEvent(
                    event_type="message_start",
                    data={"agent_id": agent_id, "model": "deepseek/deepseek-v3.2", "provider": "OpenRouter"}
                )
                
                await client.query(prompt=message)
                
                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                yield ChatStreamEvent(
                                    event_type="content_delta",
                                    data={"text": block.text}
                                )
                            
                            elif isinstance(block, ToolUseBlock):
                                tool_call = ToolCall(
                                    id=block.id,
                                    name=block.name,
                                    input=block.input,
                                    status="completed"
                                )
                                
                                yield ChatStreamEvent(
                                    event_type="tool_use_start",
                                    data={
                                        "tool_call_id": tool_call.id,
                                        "tool_name": tool_call.name
                                    }
                                )
                                
                                yield ChatStreamEvent(
                                    event_type="tool_use_stop",
                                    data={"tool_call": tool_call.model_dump()}
                                )
                
                yield ChatStreamEvent(
                    event_type="message_stop",
                    data={"stop_reason": "end_turn"}
                )
        
        except Exception as e:
            yield ChatStreamEvent(
                event_type="error",
                data={"error": str(e), "type": type(e).__name__}
            )
