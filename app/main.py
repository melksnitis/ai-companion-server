# CRITICAL: Apply Letta patch BEFORE any other imports
# This uses wrapt's post import hooks to patch modules before they're cached
from app.utils.letta_patch import apply_letta_patch
apply_letta_patch()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import uuid

from app.config import settings
from app.models.database import init_db, async_session
from app.routers import chat_router, memory_router, workspace_router, tools_router
from app.services import AgentService, MemoryService
from app.models.schemas import ChatMessage


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for the Evolving Personal AI Assistant",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(workspace_router)
app.include_router(tools_router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "endpoints": {
            "chat": "/chat/stream",
            "memory": "/memory",
            "workspace": "/workspace",
            "tools": "/tools",
            "websocket": "/ws",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_event(self, client_id: str, event_type: str, data: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json({
                "event": event_type,
                "data": data,
            })


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)
    
    await manager.send_event(client_id, "connected", {"client_id": client_id})
    
    conversation_id = None
    messages: list[ChatMessage] = []
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "chat":
                message_text = data.get("message", "")
                conversation_id = data.get("conversation_id") or conversation_id or str(uuid.uuid4())
                include_memory = data.get("include_memory", True)
                
                messages.append(ChatMessage(role="user", content=message_text))
                
                await manager.send_event(client_id, "conversation_id", {"id": conversation_id})
                
                agent_service = AgentService()
                memory_labels = ["human", "persona", "preferences", "knowledge"] if include_memory else None
                
                assistant_content = ""
                
                async for event in agent_service.stream_chat(
                    message=message_text,
                    conversation_id=conversation_id,
                    memory_labels=memory_labels,
                ):
                    await manager.send_event(client_id, event.event_type, event.data)
                    
                    if event.event_type == "content_delta":
                        assistant_content += event.data.get("text", "")
                
                if assistant_content:
                    messages.append(ChatMessage(role="assistant", content=assistant_content))
                
                await manager.send_event(client_id, "done", {})
            
            elif action == "get_memory":
                async with async_session() as db:
                    memory_service = MemoryService(db)
                    context = await memory_service.get_memory_context()
                    await manager.send_event(client_id, "memory_context", {"context": context})
            
            elif action == "list_files":
                from app.services import WorkspaceService
                workspace_service = WorkspaceService()
                path = data.get("path", ".")
                tree = workspace_service.get_file_tree(path=path)
                await manager.send_event(client_id, "file_tree", tree.model_dump())
            
            elif action == "ping":
                await manager.send_event(client_id, "pong", {})
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        await manager.send_event(client_id, "error", {"error": str(e)})
        manager.disconnect(client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
