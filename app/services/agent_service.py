"""
Simplified Agent Service using Claude Agent SDK + Letta Learning SDK
Based on: https://github.com/letta-ai/learning-sdk/blob/main/examples/claude_research_agent
"""

import os
from typing import AsyncGenerator, Optional, List, Dict, Any
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock
from agentic_learning import learning

from app.config import settings
from app.models.schemas import ChatStreamEvent, ToolCall


class AgentService:
    """Simplified agent service using Claude Agent SDK with Letta memory.
    
    Model routing is handled by Claude Code Router - the agent simply uses
    whatever model the router directs requests to based on routing rules.
    """
    
    def __init__(self):
        # Use OpenRouter API key (Claude Code Router will handle model selection)
        os.environ["ANTHROPIC_API_KEY"] = settings.openrouter_api_key or settings.anthropic_api_key
            
        if settings.letta_api_key:
            os.environ["LETTA_API_KEY"] = settings.letta_api_key
        
        self.agent_name = settings.letta_agent_name
    
    def _get_agent_options(self) -> ClaudeAgentOptions:
        """Configure Claude Agent SDK options with tools.
        
        Model selection is handled by Claude Code Router based on routing rules.
        No need to specify model or base URL here.
        """
        return ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Search"],
        )
    
    async def stream_chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        memory_labels: Optional[List[str]] = None,
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """
        Stream a chat response using Claude Agent SDK wrapped in Letta learning context.
        
        Args:
            message: User message
            conversation_id: Optional conversation ID (used as agent ID in Letta)
            memory_labels: Memory block labels to use (default: ["human", "persona", "preferences"])
        """
        agent_id = conversation_id or self.agent_name
        memory_config = memory_labels or ["human", "persona", "preferences", "knowledge"]
        
        options = self._get_agent_options()
        
        yield ChatStreamEvent(
            event_type="thinking_start",
            data={"message": "Thinking..."}
        )
        
        try:
            async with learning(agent=agent_id, memory=memory_config):
                async with ClaudeSDKClient(options=options) as client:
                    yield ChatStreamEvent(
                        event_type="thinking_stop",
                        data={}
                    )
                    
                    yield ChatStreamEvent(
                        event_type="message_start",
                        data={"agent_id": agent_id, "note": "Model selected by Claude Code Router"}
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
    
    async def get_conversation_history(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get conversation history from Letta for an agent."""
        from agentic_learning import AgenticLearning
        
        client = AgenticLearning(base_url=settings.letta_base_url)
        agent = agent_id or self.agent_name
        
        try:
            messages = client.messages.list(agent=agent)
            return messages
        except Exception:
            return []
    
    async def search_memories(self, query: str, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search agent memories in Letta."""
        from agentic_learning import AgenticLearning
        
        client = AgenticLearning(base_url=settings.letta_base_url)
        agent = agent_id or self.agent_name
        
        try:
            results = client.memory.search(agent=agent, query=query)
            return results
        except Exception:
            return []
