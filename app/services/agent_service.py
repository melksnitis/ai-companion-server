"""
Agent Service using Claude Agent SDK with OpenRouter + Letta Learning SDK
Combines OpenRouter's model routing with Letta's persistent memory and learning.
Based on: https://github.com/letta-ai/learning-sdk/blob/main/examples/claude_research_agent
"""

import logging
import os
from dataclasses import asdict
from typing import AsyncGenerator, Optional, List, Dict, Any
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from agentic_learning import learning

from app.config import settings
from app.models.schemas import ChatStreamEvent, ToolCall

logger = logging.getLogger(__name__)

class AgentService:
    """Agent service using Claude Agent SDK with OpenRouter and Letta Learning SDK.

    Architecture:
    - OpenRouter: Provides access to DeepSeek v3.2 and other models
    - Claude Agent SDK: Native tool execution (Bash, Read, Write, Edit, etc.)
    - Letta Learning SDK: Persistent memory and continual learning (patched)

    The learning context wraps the Claude Agent SDK to provide memory persistence.
    A monkey patch enables Letta to accept DeepSeek conversations by overriding provider="letta".
    """
    
    def __init__(self):
        # Configure Claude Agent SDK to use OpenRouter (via proxy if enabled)
        # Proxy rewrites all model fields to force free model usage
        proxy_url = os.environ.get("OPENROUTER_PROXY_URL")
        if proxy_url:
            os.environ["ANTHROPIC_BASE_URL"] = proxy_url
            print(f"[AgentService] Using proxy: {proxy_url}")
        else:
            os.environ["ANTHROPIC_BASE_URL"] = "https://openrouter.ai/api"
        os.environ["ANTHROPIC_AUTH_TOKEN"] = settings.openrouter_api_key
        os.environ["ANTHROPIC_API_KEY"] = ""  # Must be explicitly empty to prevent conflicts
        os.environ["OPENROUTER_MODEL_ID"] = settings.openrouter_model_id  # Ensure Letta saves correct model
        
        # Configure Letta Learning SDK
        if settings.letta_api_key:
            os.environ["LETTA_API_KEY"] = settings.letta_api_key
        if settings.letta_base_url:
            os.environ["LETTA_BASE_URL"] = settings.letta_base_url
        
        self.agent_name = settings.letta_agent_name
        self._configure_sleeptime_agent()
    
    def _get_agent_options(self) -> ClaudeAgentOptions:
        """Configure Claude Agent SDK options with tools and MCP servers.
        
        Model selection is handled by OpenRouter.
        Uses DeepSeek v3.2 by default, can be overridden with ANTHROPIC_DEFAULT_SONNET_MODEL env var.
        Workspace is set to /app/workspace for file operations.
        MCP servers are loaded from config/mcp_servers.json.
        """
        # Set Todoist API token for MCP server
        if settings.todoist_api_token:
            os.environ["TODOIST_API_TOKEN"] = settings.todoist_api_token
        
        # Set Google OAuth credentials for MCP server
        if settings.google_oauth_credentials:
            abs_creds_path = os.path.abspath(settings.google_oauth_credentials)
            os.environ["GOOGLE_OAUTH_CREDENTIALS"] = abs_creds_path
            print(f"[MCP] Set GOOGLE_OAUTH_CREDENTIALS={abs_creds_path}")
        else:
            print(f"[MCP] WARNING: google_oauth_credentials not set in settings!")
        
        # Get absolute path to MCP config (since cwd is set to workspace)
        mcp_config_path = os.path.abspath("./config/mcp_servers.json")
        print(f"[MCP] Loading MCP config from: {mcp_config_path}")
        print(f"[MCP] Config file exists: {os.path.exists(mcp_config_path)}")
        
        model_id = settings.openrouter_model_id
        print(f"[AgentService] _get_agent_options using model={model_id}", flush=True)
        os.environ.setdefault("CLAUDE_CLI_DEFAULT_TOOLS", "0")
        instructions = (
            "Web research policy:\n"
            "- You MUST use the searxng MCP tools (mcp__searxng-enhanced__search_web and "
            "mcp__searxng-enhanced__get_website) for every web lookup.\n"
            "- You MUST NOT call the legacy WebSearch/WebFetch/Task/TaskOutput tools. "
            "If you need search results, invoke the searxng MCP tools instead.\n"
            "- If the searxng MCP server is unavailable, explain that web search is temporarily "
            "blocked and ask the user how to proceed."
        )
        cli_path = (
            settings.claude_cli_path
            or os.environ.get("CLAUDE_CLI_PATH")
            or "/usr/local/bin/claude"
        )
        print(f"[AgentService] Using Claude CLI at: {cli_path}", flush=True)
        return ClaudeAgentOptions(
            permission_mode="dontAsk",
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "mcp__searxng-enhanced__search_web", "mcp__searxng-enhanced__get_website", "mcp__searxng-enhanced__get_current_datetime", 
                "mcp__todoist__todoist_create_task", "mcp__todoist__todoist_complete_task", "mcp__todoist__todoist_get_tasks",
                "mcp__google-calendar__list-calendars", "mcp__google-calendar__list-events", "mcp__google-calendar__search-events", "mcp__google-calendar__get-event", "mcp__google-calendar__get-current-time"],
            model=model_id,
            cwd="./workspace",  # Set working directory for file operations (local)
            mcp_servers=mcp_config_path,  # MCP servers configuration (absolute path)
            cli_path="/usr/local/Cellar/node/23.6.1/bin/claude",  # Path to Claude CLI
        )
    
    @staticmethod
    def _enforce_tool_policy(tool_name: str, allowed: bool) -> bool:
        """Force disallowed tools to be rejected with guidance."""
        legacy = {"WebSearch", "WebFetch", "Task", "TaskOutput"}
        if tool_name in legacy:
            raise PermissionError(
                f"{tool_name} is disabled. Please use the searxng MCP tools "
                "(mcp__searxng-enhanced__search_web / get_website) for web access."
            )
        return allowed
    
    def _configure_sleeptime_agent(self) -> None:
        """Ensure the Letta agent has sleeptime enabled with desired frequency."""
        try:
            from agentic_learning import AgenticLearning
            client = AgenticLearning()
            
            agent = client.agents.retrieve(agent=self.agent_name)
            if not agent:
                default_memory = ["human", "persona", "preferences", "knowledge"]
                agent = client.agents.create(
                    agent=self.agent_name,
                    memory=default_memory,
                    model=settings.openrouter_model_id,
                )
                print(f"[Sleeptime] Created Letta agent '{self.agent_name}' with sleeptime enabled.")
            
            client.agents.sleeptime.update(
                agent=self.agent_name,
                model=settings.openrouter_model_id,
                frequency=settings.letta_sleeptime_frequency,
            )
            print(f"[Sleeptime] Configured frequency={settings.letta_sleeptime_frequency} turns for agent '{self.agent_name}'.")
        except Exception as exc:
            print(f"[Sleeptime] WARNING: Failed to configure sleeptime agent ({exc})")
    
    async def stream_chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        memory_labels: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """Stream a chat response using Claude Agent SDK wrapped in Letta learning context.

        Args:
            message: User message to send
            conversation_id: Optional conversation ID (used as agent ID in Letta)
            memory_labels: Memory block labels to use (default: ["human", "persona", "preferences"])
            session_id: Optional Claude SDK session ID to resume previous conversation
        """
        agent_id = conversation_id or self.agent_name
        memory_config = memory_labels or ["human", "persona", "preferences", "knowledge"]
        
        options = self._get_agent_options()
        options.include_partial_messages = True
        
        # Add session resumption if session_id provided
        if session_id:
            options.resume = session_id
            print(f"[SESSION] Resuming session: {session_id}")
        
        yield ChatStreamEvent(
            event_type="thinking_start",
            data={"message": "Thinking..."}
        )
        
        try:
            # Wrap Claude Agent SDK in Letta learning context for memory persistence
            # ClaudeInterceptor will automatically inject memory from Letta into system prompt
            async with learning(agent=agent_id, memory=memory_config):
                async with ClaudeSDKClient(options=options) as client:
                    yield ChatStreamEvent(
                        event_type="thinking_stop",
                        data={}
                    )
                    
                    yield ChatStreamEvent(
                        event_type="message_start",
                        data={
                            "agent_id": agent_id,
                            "model": settings.openrouter_model_id,
                            "provider": "OpenRouter",
                            "memory_enabled": True,
                            "memory_blocks": memory_config
                        }
                    )
                    
                    await client.query(prompt=message)
                    
                    captured_session_id = None
                    active_tool_calls: Dict[str, ToolCall] = {}
                    
                    async for msg in client.receive_response():
                        if isinstance(msg, SystemMessage):
                            data = msg.data or {}
                            yield ChatStreamEvent(
                                event_type="system_message",
                                data=data,
                            )
                            
                            if msg.subtype == "init":
                                if 'session_id' in data:
                                    captured_session_id = data['session_id']
                                    print(f"[SESSION] Captured session ID: {captured_session_id}")
                                    yield ChatStreamEvent(
                                        event_type="system_init",
                                        data=data,
                                    )
                                    yield ChatStreamEvent(
                                        event_type="session_id",
                                        data={"session_id": captured_session_id}
                                    )
                        
                        elif isinstance(msg, UserMessage):
                            yield ChatStreamEvent(
                                event_type="user_message",
                                data={"message": asdict(msg)},
                            )
                        
                        elif isinstance(msg, StreamEvent):
                            yield ChatStreamEvent(
                                event_type="assistant_partial",
                                data={"message": asdict(msg)},
                            )
                        
                        elif isinstance(msg, AssistantMessage):
                            yield ChatStreamEvent(
                                event_type="assistant_message",
                                data={"message": asdict(msg)},
                            )
                            
                            for block in msg.content:
                                if isinstance(block, TextBlock):
                                    yield ChatStreamEvent(
                                        event_type="content_delta",
                                        data={"text": block.text}
                                    )
                                
                                elif isinstance(block, ThinkingBlock):
                                    yield ChatStreamEvent(
                                        event_type="thinking_delta",
                                        data={"thinking": block.thinking}
                                    )
                                
                                elif isinstance(block, ToolUseBlock):
                                    tool_call = ToolCall(
                                        id=block.id,
                                        name=block.name,
                                        input=block.input,
                                        status="running"
                                    )
                                    active_tool_calls[tool_call.id] = tool_call
                                    
                                    yield ChatStreamEvent(
                                        event_type="tool_use_start",
                                        data={
                                            "tool_call_id": tool_call.id,
                                            "tool_name": tool_call.name,
                                            "tool_input": tool_call.input,
                                        }
                                    )
                                
                                elif isinstance(block, ToolResultBlock):
                                    yield ChatStreamEvent(
                                        event_type="tool_result",
                                        data={
                                            "tool_use_id": block.tool_use_id,
                                            "content": block.content,
                                            "is_error": block.is_error,
                                        }
                                    )
                                    
                                    tool_call = active_tool_calls.get(block.tool_use_id)
                                    if tool_call:
                                        tool_call.status = "completed" if not block.is_error else "failed"
                                        yield ChatStreamEvent(
                                            event_type="tool_use_stop",
                                            data={"tool_call": tool_call.model_dump()}
                                        )
                            
                            yield ChatStreamEvent(
                                event_type="content_stop",
                                data={}
                            )
                        
                        elif isinstance(msg, ResultMessage):
                            yield ChatStreamEvent(
                                event_type="result",
                                data={"message": asdict(msg)},
                            )
                    
                    yield ChatStreamEvent(
                        event_type="message_stop",
                        data={"stop_reason": "end_turn"}
                    )
        
        except Exception as e:
            stderr_output = getattr(e, "stderr", None)
            logger.exception(
                "Claude Agent SDK session failed",
                extra={"claude_stderr": stderr_output, "conversation_id": conversation_id},
            )
            yield ChatStreamEvent(
                event_type="error",
                data={"error": str(e), "type": type(e).__name__}
            )
