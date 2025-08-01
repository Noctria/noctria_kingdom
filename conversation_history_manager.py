import json
from typing import List, Dict
from openai import OpenAI
import asyncio

class ConversationHistoryManager:
    def __init__(self, openai_client: OpenAI, max_history_length=20):
        self.openai = openai_client
        self.max_history_length = max_history_length
        self.history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        self.history.append({'role': role, 'content': content})
        if len(self.history) > self.max_history_length:
            self.history.pop(0)

    async def summarize_history(self) -> str:
        prompt = "以下の対話履歴を要約してください。重要な決定や課題も含めて簡潔に。\n\n"
        for msg in self.history:
            prompt += f"{msg['role']}: {msg['content']}\n"
        prompt += "\n要約:"

        response = await asyncio.to_thread(
            lambda: self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
        )
        summary = response.choices[0].message.content
        return summary

    def save_history(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def load_history(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            self.history = json.load(f)
