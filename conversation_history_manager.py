# src/noctria_gui/services/conversation_history_manager.py

import json
from typing import List, Dict, Optional
from fastapi import Depends
from openai import OpenAI
import asyncio
import threading

class ConversationHistoryManager:
    """
    会話履歴をユーザー単位で管理する例。
    シンプルにメモリ上のユーザー別履歴をスレッドセーフに保持。
    本格的にはDBやRedis連携を推奨。
    """

    # ユーザーIDごとの履歴保存用クラス変数（スレッドセーフ対応）
    _lock = threading.Lock()
    _user_histories: Dict[str, List[Dict[str, str]]] = {}

    def __init__(self, openai_client: OpenAI, user_id: Optional[str] = None, max_history_length: int = 20):
        self.openai = openai_client
        self.user_id = user_id or "default_user"
        self.max_history_length = max_history_length

    def _get_history(self) -> List[Dict[str, str]]:
        with self._lock:
            return self._user_histories.setdefault(self.user_id, [])

    def add_message(self, role: str, content: str):
        with self._lock:
            history = self._user_histories.setdefault(self.user_id, [])
            history.append({'role': role, 'content': content})
            if len(history) > self.max_history_length:
                history.pop(0)

    def get_history(self) -> List[Dict[str, str]]:
        with self._lock:
            return list(self._user_histories.get(self.user_id, []))  # コピーを返す

    async def summarize_history(self) -> str:
        history = self.get_history()
        prompt = "以下の対話履歴を要約してください。重要な決定や課題も含めて簡潔に。\n\n"
        for msg in history:
            prompt += f"{msg['role']}: {msg['content']}\n"
        prompt += "\n要約:"

        response = await asyncio.to_thread(
            lambda: self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
        )
        return response.choices[0].message.content

    def save_history(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.get_history(), f, ensure_ascii=False, indent=2)

    def load_history(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            history = json.load(f)
        with self._lock:
            self._user_histories[self.user_id] = history

# 依存注入用ファクトリ関数例
from fastapi import Request

def get_conversation_history_manager(
    request: Request,
    openai_client: OpenAI = Depends()  # 事前にget_openai_client()をDepends登録しておく想定
) -> ConversationHistoryManager:
    # 例: ユーザー識別にAuthorizationヘッダーやCookieを利用してuser_idを決定
    user_id = request.headers.get("X-User-ID", "default_user")
    return ConversationHistoryManager(openai_client=openai_client, user_id=user_id)
