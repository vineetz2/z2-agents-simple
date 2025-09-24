"""
Database helper functions for conversation persistence
"""
from models import Conversation, Message, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Dict, Optional
import uuid
import json
import logging

logger = logging.getLogger(__name__)

async def get_or_create_conversation(conversation_id: str, db: AsyncSession) -> Conversation:
    """Get existing conversation or create new one"""
    try:
        # Try to get existing conversation
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            # Create new conversation
            conversation = Conversation(
                id=conversation_id,
                meta_data={}
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            logger.info(f"Created new conversation: {conversation_id}")
        else:
            logger.info(f"Retrieved existing conversation: {conversation_id}")

        return conversation
    except Exception as e:
        logger.error(f"Error in get_or_create_conversation: {e}")
        await db.rollback()
        raise

async def save_message(
    conversation_id: str,
    role: str,
    content: str,
    agent_type: Optional[str],
    db: AsyncSession,
    meta_data: Optional[Dict] = None
) -> Message:
    """Save a message to the database"""
    try:
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content if isinstance(content, str) else json.dumps(content),
            agent_type=agent_type,
            meta_data=meta_data or {}
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        logger.info(f"Saved {role} message to conversation {conversation_id}")
        return message
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        await db.rollback()
        raise

async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession,
    limit: int = 20
) -> List[Dict]:
    """Get recent conversation history"""
    try:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()

        # Convert to list of dicts and reverse to get chronological order
        history = []
        for msg in reversed(messages):
            history.append({
                "role": msg.role,
                "content": msg.content,
                "agent_type": msg.agent_type,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })

        logger.info(f"Retrieved {len(history)} messages for conversation {conversation_id}")
        return history
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return []

async def format_history_for_llm(history: List[Dict]) -> str:
    """Format conversation history for LLM context"""
    if not history:
        return ""

    formatted = ""
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        # Handle JSON content
        content = msg["content"]
        if content.startswith('{') or content.startswith('['):
            try:
                import json
                parsed = json.loads(content)
                if isinstance(parsed, dict) and 'content' in parsed:
                    content = str(parsed['content'])
            except:
                pass

        # Truncate very long messages
        if len(content) > 500:
            content = content[:500] + "..."
        formatted += f"{role}: {content}\n"

    return formatted.strip()

async def clear_old_conversations(db: AsyncSession, days_old: int = 30):
    """Clean up old conversations (optional maintenance function)"""
    from datetime import datetime, timedelta

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        result = await db.execute(
            select(Conversation).where(Conversation.updated_at < cutoff_date)
        )
        old_conversations = result.scalars().all()

        for conv in old_conversations:
            await db.delete(conv)

        await db.commit()
        logger.info(f"Deleted {len(old_conversations)} old conversations")
        return len(old_conversations)
    except Exception as e:
        logger.error(f"Error clearing old conversations: {e}")
        await db.rollback()
        return 0