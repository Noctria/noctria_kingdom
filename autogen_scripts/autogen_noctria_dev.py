import asyncio
import os
import pathlib
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEYが設定されていません。")

    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)

    assistant = AssistantAgent(
        name="Noctria_Assistant",
        system_message="あなたは、FX自動トレードシステムの設計を支援する優秀なAIアシスタントです。具体的で実践的な提案を行ってください。",
        model_client=client,
    )

    user_message = (
        "USD/JPY FXの自動トレードAIをFintokei＋MT5の制約のもとで設計します。"
        "まず、最適な全体設計案を、具体的なファイル構成と主要なクラス名を含めて提案してください。"
    )

    # 同期API createをasyncio.to_threadで非同期呼び出し
    response = await asyncio.to_thread(
        lambda: assistant._model_client.create(
            messages=[{"role": "user", "content": user_message}]
        )
    )

    print("AI response:", response.choices[0].message.content)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
