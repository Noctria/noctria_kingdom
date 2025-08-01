from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
import os
import asyncio

from conversation_history_manager import ConversationHistoryManager

router = APIRouter()

def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEYが設定されていません。")
    return OpenAI(api_key=api_key)

def get_history_manager() -> ConversationHistoryManager:
    return ConversationHistoryManager()

@router.post("/chat")
async def chat(
    request: Request,
    client: OpenAI = Depends(get_openai_client),
    history_mgr: ConversationHistoryManager = Depends(get_history_manager)
):
    data = await request.json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return JSONResponse({"error": "メッセージが空です"}, status_code=400)

    history_mgr.add_message("user", user_msg)

    response = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model="gpt-4o",
            messages=history_mgr.get_history()
        )
    )
    assistant_msg = response.choices[0].message.content
    history_mgr.add_message("assistant", assistant_msg)

    return JSONResponse({"reply": assistant_msg})
