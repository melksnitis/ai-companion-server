from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.models import MemoryBlock, MemoryBlockType
from app.models.database import get_db
from app.services import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/", response_model=MemoryBlock)
async def create_memory(
    memory: MemoryBlock,
    db: AsyncSession = Depends(get_db),
):
    service = MemoryService(db)
    return await service.create_memory(memory)


@router.get("/", response_model=List[MemoryBlock])
async def list_memories(
    type: Optional[MemoryBlockType] = Query(None, description="Filter by memory type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = MemoryService(db)
    return await service.list_memories(block_type=type, limit=limit, offset=offset)


@router.get("/context")
async def get_memory_context(
    db: AsyncSession = Depends(get_db),
):
    service = MemoryService(db)
    context = await service.get_memory_context()
    return {"context": context}


@router.get("/search")
async def search_memories(
    q: str = Query(..., description="Search query"),
    type: Optional[MemoryBlockType] = Query(None, description="Filter by memory type"),
    db: AsyncSession = Depends(get_db),
):
    service = MemoryService(db)
    results = await service.search_memories(query=q, block_type=type)
    return results


@router.get("/{memory_id}", response_model=MemoryBlock)
async def get_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = MemoryService(db)
    memory = await service.get_memory(memory_id)
    
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return memory


@router.put("/{memory_id}", response_model=MemoryBlock)
async def update_memory(
    memory_id: str,
    memory: MemoryBlock,
    db: AsyncSession = Depends(get_db),
):
    service = MemoryService(db)
    
    existing = await service.get_memory(memory_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    updated = await service.update_memory(
        memory_id,
        value=memory.value,
        metadata=memory.metadata,
    )
    
    return updated


@router.post("/upsert", response_model=MemoryBlock)
async def upsert_memory(
    memory: MemoryBlock,
    db: AsyncSession = Depends(get_db),
):
    service = MemoryService(db)
    return await service.upsert_memory(memory)


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = MemoryService(db)
    
    deleted = await service.delete_memory(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return {"status": "deleted"}


@router.post("/bulk")
async def bulk_create_memories(
    memories: List[MemoryBlock],
    db: AsyncSession = Depends(get_db),
):
    service = MemoryService(db)
    created = []
    
    for memory in memories:
        result = await service.upsert_memory(memory)
        created.append(result)
    
    return {"created": len(created), "memories": created}
