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

    # UserProxyAgent と AssistantAgent をインスタンス化
    proxy = UserProxyAgent(name="Daifuku_Proxy")
    assistant = AssistantAgent(name="Noctria_Assistant", model_client=client)

    # UserProxyAgent から直接OpenAIに問い合わせる（UserProxyAgentがsend_messageを持たない場合の代替）
    user_message = (
        "USD/JPY FXの自動トレードAIをFintokei＋MT5制約のもとで設計します。"
        "まず最適な全体設計案をファイル構成・主要クラス名付きで提案してください。"
    )

    # ここではUserProxyAgentを使わずにAssistantAgentを直接呼び出す例
    response = await assistant._model_client.chat.completions.acreate(
        model=assistant._model_client.model,
        messages=[{"role": "user", "content": user_message}]
    )
    print("AI response:", response.choices[0].message.content)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
