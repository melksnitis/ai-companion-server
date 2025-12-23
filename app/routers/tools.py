from fastapi import APIRouter

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/")
async def list_tools():
    """List available Claude Agent SDK tools."""
    return {
        "info": "Tools are executed natively by Claude Agent SDK during chat interactions",
        "tools": [
            {
                "name": "Bash",
                "description": "Execute shell commands in the workspace",
                "native": True,
            },
            {
                "name": "Read",
                "description": "Read file contents from the workspace",
                "native": True,
            },
            {
                "name": "Write",
                "description": "Create or overwrite files in the workspace",
                "native": True,
            },
            {
                "name": "Edit",
                "description": "Find and replace text in files",
                "native": True,
            },
            {
                "name": "Glob",
                "description": "List files matching glob patterns",
                "native": True,
            },
            {
                "name": "Search",
                "description": "Search for text patterns in files",
                "native": True,
            },
        ],
        "note": "Tools are automatically available during chat. Use /chat/stream or /ws endpoints to interact with the agent.",
    }
