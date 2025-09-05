from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncpg
import os

# --- ここを追加 ---
from dotenv import load_dotenv, find_dotenv
# 1. .env.local > .env の順で読み込む
load_dotenv(find_dotenv('.env.local'), override=True)
load_dotenv(find_dotenv('.env'), override=False)  # .envは上書きしない
# --- ここまで ---

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URLが設定されていません。")

class ChatMessage(BaseModel):
    role: str
    content: str

@router.on_event("startup")
async def startup():
    router.db_pool = await asyncpg.create_pool(DATABASE_URL)

@router.on_event("shutdown")
async def shutdown():
    await router.db_pool.close()

@router.get("/chat_history", response_model=List[Dict[str, Any]])
async def get_chat_history():
    async with router.db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT timestamp, role, content FROM chat_history ORDER BY timestamp ASC"
        )
        history = [
            {
                "timestamp": row["timestamp"].isoformat(),
                "role": row["role"],
                "content": row["content"],
            }
            for row in rows
        ]
    return JSONResponse(content=history)

@router.post("/chat_history")
async def post_chat_message(message: ChatMessage):
    async with router.db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_history (role, content) VALUES ($1, $2)",
            message.role,
            message.content,
        )
    return {"status": "success"}
