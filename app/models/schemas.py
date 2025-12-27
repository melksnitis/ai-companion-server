from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class MemoryBlockType(str, Enum):
    PERSONA = "persona"
    PREFERENCES = "preferences"
    KNOWLEDGE = "knowledge"
    REFLECTION = "reflection"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None  # Claude SDK session ID for resumption/forking
    include_memory: bool = True
    tools_enabled: bool = True
    stream: bool = True


class ToolCall(BaseModel):
    id: str
    name: str
    input: Dict[str, Any]
    status: Literal["pending", "running", "completed", "failed"] = "pending"


class ToolResult(BaseModel):
    tool_call_id: str
    output: Any
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


class ChatStreamEvent(BaseModel):
    event_type: Literal[
        "conversation_id",
        "session_id",
        "message_start",
        "content_delta", 
        "content_stop",
        "tool_use_start",
        "tool_use_delta",
        "tool_use_stop",
        "tool_result",
        "message_stop",
        "error",
        "thinking_start",
        "thinking_stop",
    ]
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MemoryBlock(BaseModel):
    id: Optional[str] = None
    type: MemoryBlockType
    key: str
    value: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkspaceFile(BaseModel):
    path: str
    name: str
    is_directory: bool
    size: Optional[int] = None
    modified_at: Optional[datetime] = None
    children: Optional[List["WorkspaceFile"]] = None


class ConversationHistory(BaseModel):
    id: str
    title: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None


WorkspaceFile.model_rebuild()
