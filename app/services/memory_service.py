from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime
import uuid

from app.models.schemas import MemoryBlock, MemoryBlockType
from app.models.database import MemoryBlockDB, MemoryBlockTypeDB


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _to_db_type(self, block_type: MemoryBlockType) -> MemoryBlockTypeDB:
        return MemoryBlockTypeDB(block_type.value)
    
    def _from_db(self, db_block: MemoryBlockDB) -> MemoryBlock:
        return MemoryBlock(
            id=db_block.id,
            type=MemoryBlockType(db_block.type.value),
            key=db_block.key,
            value=db_block.value,
            metadata=db_block.extra_data,
            created_at=db_block.created_at,
            updated_at=db_block.updated_at,
        )
    
    async def create_memory(self, memory: MemoryBlock) -> MemoryBlock:
        memory_id = memory.id or str(uuid.uuid4())
        
        db_block = MemoryBlockDB(
            id=memory_id,
            type=self._to_db_type(memory.type),
            key=memory.key,
            value=memory.value,
            extra_data=memory.metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        self.db.add(db_block)
        await self.db.commit()
        await self.db.refresh(db_block)
        
        return self._from_db(db_block)
    
    async def get_memory(self, memory_id: str) -> Optional[MemoryBlock]:
        result = await self.db.execute(
            select(MemoryBlockDB).where(MemoryBlockDB.id == memory_id)
        )
        db_block = result.scalar_one_or_none()
        
        return self._from_db(db_block) if db_block else None
    
    async def get_memory_by_key(
        self, 
        block_type: MemoryBlockType, 
        key: str
    ) -> Optional[MemoryBlock]:
        result = await self.db.execute(
            select(MemoryBlockDB).where(
                MemoryBlockDB.type == self._to_db_type(block_type),
                MemoryBlockDB.key == key
            )
        )
        db_block = result.scalar_one_or_none()
        
        return self._from_db(db_block) if db_block else None
    
    async def list_memories(
        self, 
        block_type: Optional[MemoryBlockType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MemoryBlock]:
        query = select(MemoryBlockDB)
        
        if block_type:
            query = query.where(MemoryBlockDB.type == self._to_db_type(block_type))
        
        query = query.order_by(MemoryBlockDB.updated_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        db_blocks = result.scalars().all()
        
        return [self._from_db(block) for block in db_blocks]
    
    async def update_memory(
        self, 
        memory_id: str, 
        value: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[MemoryBlock]:
        update_data = {"updated_at": datetime.utcnow()}
        
        if value is not None:
            update_data["value"] = value
        if metadata is not None:
            update_data["extra_data"] = metadata
        
        await self.db.execute(
            update(MemoryBlockDB)
            .where(MemoryBlockDB.id == memory_id)
            .values(**update_data)
        )
        await self.db.commit()
        
        return await self.get_memory(memory_id)
    
    async def upsert_memory(self, memory: MemoryBlock) -> MemoryBlock:
        existing = await self.get_memory_by_key(memory.type, memory.key)
        
        if existing:
            return await self.update_memory(
                existing.id,
                value=memory.value,
                metadata=memory.metadata
            )
        else:
            return await self.create_memory(memory)
    
    async def delete_memory(self, memory_id: str) -> bool:
        result = await self.db.execute(
            delete(MemoryBlockDB).where(MemoryBlockDB.id == memory_id)
        )
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def get_memory_context(self) -> str:
        context_parts = []
        
        for block_type in MemoryBlockType:
            memories = await self.list_memories(block_type=block_type, limit=20)
            
            if memories:
                context_parts.append(f"### {block_type.value.title()}")
                for mem in memories:
                    context_parts.append(f"- **{mem.key}**: {mem.value}")
                context_parts.append("")
        
        return "\n".join(context_parts) if context_parts else ""
    
    async def search_memories(
        self, 
        query: str,
        block_type: Optional[MemoryBlockType] = None,
    ) -> List[MemoryBlock]:
        sql_query = select(MemoryBlockDB).where(
            MemoryBlockDB.value.ilike(f"%{query}%") |
            MemoryBlockDB.key.ilike(f"%{query}%")
        )
        
        if block_type:
            sql_query = sql_query.where(
                MemoryBlockDB.type == self._to_db_type(block_type)
            )
        
        result = await self.db.execute(sql_query)
        db_blocks = result.scalars().all()
        
        return [self._from_db(block) for block in db_blocks]
