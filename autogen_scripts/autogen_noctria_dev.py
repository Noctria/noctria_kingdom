from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
import asyncio
import os
from dotenv import load_dotenv
import pathlib

env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEYが設定されていません。")

    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)

    proxy = UserProxyAgent(name="Daifuku_Proxy")
    assistant = AssistantAgent(name="Noctria_Assistant", model_client=client)

    # 代理ユーザーからのメッセージをAssistantに送る
    user_message = (
        "USD/JPY FXの自動トレードAIをFintokei＋MT5の制約のもとで設計します。"
        "まず、最適な全体設計案を、具体的なファイル構成と主要なクラス名を含めて提案してください。"
    )

    # send_messageを使う（もし存在しないなら下記を参照）
    try:
        response = await proxy.send_message(user_message, assistant)
        print("AI response:", response)
    except AttributeError:
        # send_messageが無ければ直接APIを呼び出す方法へフォールバック
        response = await assistant._model_client.acreate(
            messages=[{"role": "user", "content": user_message}]
        )
        print("AI response:", response.choices[0].message.content)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
