from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
import asyncio
import os
from dotenv import load_dotenv
import pathlib

# .envから環境変数を読み込む（スクリプトの2階層上にある場合）
env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

async def main():
    # 明示的にAPIキーを渡すのが確実
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEYが環境変数に設定されていません。")

    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)

    proxy = UserProxyAgent(name="Daifuku_Proxy")
    assistant = AssistantAgent(name="Noctria_Assistant", model_client=client)

    # UserProxyAgentにメッセージを送って会話開始
    user_message = (
        "USD/JPY FXの自動トレードAIをFintokei＋MT5制約のもとで設計します。"
        "まず最適な全体設計案をファイル構成・主要クラス名付きで提案してください。"
    )

    # UserProxyAgentのsend_message()を使ってメッセージを送る
    response = await proxy.send_message(user_message, assistant)

    print("AI response:", response)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
