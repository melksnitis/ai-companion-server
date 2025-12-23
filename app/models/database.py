from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Text, DateTime, JSON, Enum as SQLEnum
from datetime import datetime
import enum

from app.config import settings


class Base(DeclarativeBase):
    pass


class MemoryBlockTypeDB(enum.Enum):
    PERSONA = "persona"
    PREFERENCES = "preferences"
    KNOWLEDGE = "knowledge"
    REFLECTION = "reflection"


class MemoryBlockDB(Base):
    __tablename__ = "memory_blocks"
    
    id = Column(String, primary_key=True)
    type = Column(SQLEnum(MemoryBlockTypeDB), nullable=False)
    key = Column(String, nullable=False, index=True)
    value = Column(Text, nullable=False)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationDB(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=True)
    messages = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_data = Column(JSON, nullable=True)


engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
