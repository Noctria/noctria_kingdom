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
        raise RuntimeError("OPENAI_API_KEYが環境変数に設定されていません。")

    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)

    proxy = UserProxyAgent(name="Daifuku_Proxy")
    assistant = AssistantAgent(name="Noctria_Assistant", model_client=client)

    initial_message = (
        "USD/JPY FXの自動トレードAIをFintokei＋MT5制約のもとで設計します。"
        "まず最適な全体設計案をファイル構成・主要クラス名付きで提案してください。"
    )

    # 代理AIとアシスタントAIの対話を実行
    response = await proxy.run_conversation(assistant, initial_message, max_turns=6)

    print("AI response:", response)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
