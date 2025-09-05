from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from openai import OpenAI
import os
import asyncio

#from .chat_history_api import chat_manager  # chat_history_api の chat_manager を利用

router = APIRouter()

def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEYが設定されていません。")
    return OpenAI(api_key=api_key)

@router.post("/chat")
async def chat(
    request: Request,
    client: OpenAI = Depends(get_openai_client),
):
    data = await request.json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return JSONResponse({"error": "メッセージが空です"}, status_code=400)

    # ユーザーメッセージを履歴に追加
    chat_manager.add_message("user", user_msg)

    # OpenAI API へ履歴を渡して応答を取得
    response = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model="gpt-4o",
            messages=chat_manager.get_history()
        )
    )
    assistant_msg = response.choices[0].message.content

    # アシスタント応答を履歴に追加
    chat_manager.add_message("assistant", assistant_msg)

    return JSONResponse({"reply": assistant_msg})
