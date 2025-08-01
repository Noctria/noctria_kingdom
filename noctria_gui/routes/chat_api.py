from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from openai import OpenAI
from conversation_history_manager import ConversationHistoryManager
import asyncio

router = APIRouter()

# グローバルで履歴管理（単純例）
history_mgr = None
client = None

@router.on_event("startup")
async def startup_event():
    global client, history_mgr
    client = OpenAI(api_key="YOUR_API_KEY")  # 実際は環境変数等から取得推奨
    history_mgr = ConversationHistoryManager(client)

@router.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return JSONResponse({"error": "メッセージが空です"}, status_code=400)

    history_mgr.add_message("user", user_msg)

    response = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model="gpt-4o",
            messages=history_mgr.history
        )
    )
    assistant_msg = response.choices[0].message.content
    history_mgr.add_message("assistant", assistant_msg)

    return JSONResponse({"reply": assistant_msg})
