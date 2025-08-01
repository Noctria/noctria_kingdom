import asyncio
import os
import pathlib
from dotenv import load_dotenv

# --- 修正点 ---
# autogen-agentchatパッケージの正しいimportに変更
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent

# .envファイルのパスを正しく設定
# このスクリプトの親ディレクトリの親ディレクトリにある.envファイルを読み込む
env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

async def main():
    # 環境変数からAPIキーを読み込む
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("環境変数 'OPENAI_API_KEY' が設定されていません。")

    # LLMのモデル設定
    # gpt-4oモデルを使用し、APIキーを設定
    config_list = [
        {
            "model": "gpt-4o",
            "api_key": api_key,
        }
    ]

    # アシスタントエージェントを定義
    # システムメッセージでAIの役割を明確に設定
    assistant = AssistantAgent(
        name="Noctria_Assistant",
        system_message="あなたは、FX自動トレードシステムの設計を支援する優秀なAIアシスタントです。具体的で実践的な提案を行ってください。",
        llm_config={"config_list": config_list},
    )

    # ユーザープロキシエージェントを定義
    # このエージェントがユーザーの代わりにアシスタントと対話する
    proxy = UserProxyAgent(
        name="Daifuku_Proxy",
        human_input_mode="NEVER",  # ユーザーからの入力を待たずに処理を続ける
        max_consecutive_auto_reply=1, # 連続自動応答を1回に制限
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    )

    # ユーザーからの最初のメッセージ
    user_message = (
        "USD/JPY FXの自動トレードAIをFintokei＋MT5の制約のもとで設計します。"
        "まず、最適な全体設計案を、具体的なファイル構成と主要なクラス名を含めて提案してください。"
    )

    # UserProxyAgentからAssistantAgentにチャットを開始する
    # これにより、エージェント間で適切にメッセージがやり取りされる
    await proxy.initiate_chat(
        assistant,
        message=user_message,
    )


if __name__ == "__main__":
    # 非同期関数mainを実行する
    asyncio.run(main())
