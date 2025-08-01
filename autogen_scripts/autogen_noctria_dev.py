import asyncio
import os
import pathlib
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient


# .envファイルのパスを正しく設定
env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

async def main():
    # 環境変数からAPIキーを読み込む
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("環境変数 'OPENAI_API_KEY' が設定されていません。")

    # OpenAIクライアントを作成
    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)

    # アシスタントエージェントを定義
    assistant = AssistantAgent(
        name="Noctria_Assistant",
        system_message="あなたは、FX自動トレードシステムの設計を支援する優秀なAIアシスタントです。具体的で実践的な提案を行ってください。",
        llm_config={"config_list": [{"model": "gpt-4o", "api_key": api_key}]},
    )

    # ユーザープロキシエージェントを定義
    proxy = UserProxyAgent(
        name="Daifuku_Proxy",
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    )

    # ユーザーからの最初のメッセージ
    user_message = (
        "USD/JPY FXの自動トレードAIをFintokei＋MT5の制約のもとで設計します。"
        "まず、最適な全体設計案を、具体的なファイル構成と主要なクラス名を含めて提案してください。"
    )

    # UserProxyAgentからAssistantAgentにチャットを開始する
    await proxy.receive(user_message, assistant)

    # クライアントを閉じる
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
