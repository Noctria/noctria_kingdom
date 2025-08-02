# noctria_gui/routes/chat_history_db_api.py

import asyncpg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import os

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL")  # 例: postgresql://user:password@localhost:5432/noctria_db

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatHistoryEntry(BaseModel):
    timestamp: str
    role: str
    content: str

@router.on_event("startup")
async def startup():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URLが設定されていません。")
    router.db_pool = await asyncpg.create_pool(DATABASE_URL)

@router.on_event("shutdown")
async def shutdown():
    await router.db_pool.close()

@router.post("/chat_history", response_model=dict)
async def post_chat_message(message: ChatMessage):
    async with router.db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_history (role, content) VALUES ($1, $2)",
            message.role,
            message.content,
        )
    return {"status": "success"}

@router.get("/chat_history", response_model=List[ChatHistoryEntry])
async def get_chat_history():
    async with router.db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT timestamp, role, content FROM chat_history ORDER BY timestamp ASC")
        history = [
            ChatHistoryEntry(
                timestamp=row["timestamp"].isoformat(),
                role=row["role"],
                content=row["content"]
            ) for row in rows
        ]
    return history
