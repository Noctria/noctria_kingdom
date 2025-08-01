import os
import asyncio
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEYが設定されていません。")

    client = OpenAI(api_key=api_key)

    user_message = "USD/JPYの自動トレードAIの設計を提案してください。"

    # 非同期でチャット補完を呼び出し
    response = await client.chat.completions.acreate(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    print("AI response:", response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(main())
