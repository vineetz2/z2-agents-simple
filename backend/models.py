"""
Simplified database models - Only essential tables
"""
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from datetime import datetime
import uuid
import os

Base = declarative_base()

class Conversation(Base):
    """Simplified conversation model"""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    meta_data = Column(JSON, default={})  # Store any extra data here
    
    # Relationship
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    """Simplified message model"""
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    agent_type = Column(String)  # 'chat', 'data', 'code'
    created_at = Column(DateTime, default=datetime.utcnow)
    meta_data = Column(JSON, default={})  # Store any extra data here
    
    # Relationship
    conversation = relationship("Conversation", back_populates="messages")

class SystemConfig(Base):
    """Single table for all system configuration"""
    __tablename__ = "system_config"
    
    key = Column(String, primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database connection
# Use SQLite for simpler local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentsimple.db")

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create async session
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()