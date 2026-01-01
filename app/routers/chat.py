from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pathlib import Path
from datetime import datetime
import json
import uuid

from app.models import ChatRequest, ChatMessage, ChatStreamEvent, ToolCall, ToolResult
from app.models.database import get_db, ConversationDB
from app.services import AgentService, MemoryService
from sqlalchemy import select

router = APIRouter(prefix="/chat", tags=["chat"])
STREAM_LOG_PATH = Path(__file__).resolve().parents[2] / "chat-stream.log"


async def get_conversation(
    conversation_id: str,
    db: AsyncSession,
) -> Optional[ConversationDB]:
    result = await db.execute(
        select(ConversationDB).where(ConversationDB.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def save_conversation(
    conversation_id: str,
    messages: List[dict],
    db: AsyncSession,
    title: Optional[str] = None,
):
    conv = await get_conversation(conversation_id, db)
    
    if conv:
        conv.messages = messages
        if title:
            conv.title = title
    else:
        conv = ConversationDB(
            id=conversation_id,
            title=title,
            messages=messages,
        )
        db.add(conv)
    
    await db.commit()


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    conv = await get_conversation(conversation_id, db) if request.conversation_id else None
    existing_messages = conv.messages if conv else []
    
    # Get session_id: prioritize request > database > None
    # This allows explicit session control (resumption, forking, or fresh start)
    # If reset_session=True, always use None to force fresh session
    session_id = None if request.reset_session else request.session_id
    if not session_id and not request.reset_session and conv and conv.extra_data:
        session_id = conv.extra_data.get("session_id")
    
    all_messages = [
        ChatMessage(role=m["role"], content=m["content"])
        for m in existing_messages
    ]
    all_messages.append(ChatMessage(role="user", content=request.message))
    
    memory_labels = ["human", "persona", "preferences", "knowledge"] if request.include_memory else None
    
    agent_service = AgentService()
    
    async def generate_stream():
        captured_events: List[dict] = []

        def record_and_yield(event_payload: dict):
            captured_events.append(event_payload)
            return f"data: {json.dumps(event_payload)}\n\n"

        yield record_and_yield({'event': 'conversation_id', 'data': {'id': conversation_id}})
        
        assistant_content = ""
        captured_session_id = session_id  # Start with existing session_id
        
        async for event in agent_service.stream_chat(
            message=request.message,
            conversation_id=conversation_id,
            memory_labels=memory_labels,
            session_id=session_id,
        ):
            payload = {'event': event.event_type, 'data': event.data}
            yield record_and_yield(payload)
            
            # Capture session_id from the event stream
            if event.event_type == "session_id":
                captured_session_id = event.data.get("session_id")
            
            if event.event_type == "content_delta":
                assistant_content += event.data.get("text", "")
        
        if assistant_content:
            all_messages.append(ChatMessage(role="assistant", content=assistant_content))
        
        # Save conversation with session_id for resumption
        conv = await get_conversation(conversation_id, db)
        if conv:
            conv.messages = [{"role": m.role, "content": m.content} for m in all_messages]
            if captured_session_id:
                conv.extra_data = {"session_id": captured_session_id}
        else:
            from app.models.database import ConversationDB
            conv = ConversationDB(
                id=conversation_id,
                messages=[{"role": m.role, "content": m.content} for m in all_messages],
                extra_data={"session_id": captured_session_id} if captured_session_id else None,
            )
            db.add(conv)
        
        await db.commit()

        STREAM_LOG_PATH.write_text(
            json.dumps(
                {
                    "saved_at": datetime.utcnow().isoformat(),
                    "conversation_id": conversation_id,
                    "events": captured_events,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        
        yield record_and_yield({'event': 'done', 'data': {}})
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConversationDB)
        .order_by(ConversationDB.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    conversations = result.scalars().all()
    
    return [
        {
            "id": conv.id,
            "title": conv.title,
            "message_count": len(conv.messages),
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
        }
        for conv in conversations
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    conv = await get_conversation(conversation_id, db)
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "id": conv.id,
        "title": conv.title,
        "messages": conv.messages,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete
    
    result = await db.execute(
        delete(ConversationDB).where(ConversationDB.id == conversation_id)
    )
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"status": "deleted"}
