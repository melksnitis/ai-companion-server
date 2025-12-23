from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.models import WorkspaceFile
from app.services import WorkspaceService

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/tree", response_model=WorkspaceFile)
async def get_file_tree(
    path: str = Query(".", description="Path relative to workspace"),
    max_depth: int = Query(3, ge=1, le=10, description="Maximum depth to traverse"),
    include_hidden: bool = Query(False, description="Include hidden files"),
):
    service = WorkspaceService()
    
    try:
        return service.get_file_tree(
            path=path,
            max_depth=max_depth,
            include_hidden=include_hidden,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files", response_model=List[WorkspaceFile])
async def list_files(
    path: str = Query(".", description="Path relative to workspace"),
    recursive: bool = Query(False, description="List recursively"),
    pattern: Optional[str] = Query(None, description="Glob pattern to filter files"),
):
    service = WorkspaceService()
    
    try:
        return service.list_files(
            path=path,
            recursive=recursive,
            pattern=pattern,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
async def get_workspace_stats():
    service = WorkspaceService()
    return service.get_workspace_stats()


@router.get("/file")
async def read_file(
    path: str = Query(..., description="Path to file relative to workspace"),
    start_line: Optional[int] = Query(None, ge=1, description="Start line (1-indexed)"),
    end_line: Optional[int] = Query(None, ge=1, description="End line (1-indexed)"),
):
    from app.services import WorkspaceService
    from pathlib import Path
    
    workspace_service = WorkspaceService()
    
    try:
        file_path = workspace_service._resolve_path(path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"Not a file: {path}")
        
        content = file_path.read_text(encoding="utf-8", errors="replace")
        
        if start_line is not None or end_line is not None:
            lines = content.splitlines(keepends=True)
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else len(lines)
            content = "".join(lines[start_idx:end_idx])
        
        return {
            "path": path,
            "content": content,
            "lines": len(content.splitlines()),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
