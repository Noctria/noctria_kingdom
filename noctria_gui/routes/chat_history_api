from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import datetime
import threading

router = APIRouter()

# スレッドセーフなメモリ内チャット履歴管理（シンプル版）
class ChatHistoryManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.history: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str):
        with self.lock:
            self.history.append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "role": role,
                "content": content
            })

    def get_history(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.history)  # コピーを返す

# シングルトン的に使う
chat_manager = ChatHistoryManager()

class ChatMessage(BaseModel):
    role: str
    content: str

@router.get("/chat_history")
async def get_chat_history():
    """
    チャット履歴を取得
    """
    return JSONResponse(content=chat_manager.get_history())

@router.post("/chat_history")
async def post_chat_message(message: ChatMessage):
    """
    チャット履歴にメッセージを追加
    """
    chat_manager.add_message(message.role, message.content)
    return {"status": "success"}
