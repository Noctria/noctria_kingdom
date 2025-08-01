# autogen_noctria_dev.py
# Python 3.10.12, venv=autogen_venv

from dotenv import load_dotenv
import os
import asyncio
import sys
import datetime

load_dotenv()

from autogen.agentchat import AssistantAgent, UserProxyAgent
from autogen.ext.openai import OpenAIChatCompletionClient

def save_log(log_text):
    fname = f"autogen_log_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(log_text)

async def main():
    try:
        client = OpenAIChatCompletionClient(model="gpt-4o")
        proxy = UserProxyAgent(
            name="Daifuku_Proxy",
            system_message=open("noctria_persona.txt", encoding="utf-8").read()
        )
        assistant = AssistantAgent(name="Noctria_Assistant", model_client=client)

        # 初回メッセージ（外部ファイル化も推奨）
        result = await proxy.initiate_chat(
            assistant,
            message="USD/JPY FXの自動トレードAIをFintokei＋MT5制約のもとで設計します。まず最適な全体設計案をファイル構成・主要クラス名付きで提案してください。",
            max_turns=6
        )
        save_log(str(result))
        await client.close()
    except Exception as e:
        print("=== AutoGen実行中にエラーが発生しました ===")
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
