from autogen.agentchat import AssistantAgent, UserProxyAgent
from autogen.ext.openai import OpenAIChatCompletionClient
import asyncio

async def main():
    # OpenAI GPT-4oでChatGPTエージェントを初期化
    client = OpenAIChatCompletionClient(model="gpt-4o")
    
    # あなたの分身AI（Noctria統治思想・Fintokei/MT5前提プロンプト）
    proxy = UserProxyAgent(
        name="Daifuku_Proxy",
        system_message="""
        あなたは「大福雅之」の分身AIです。Noctria KingdomでFintokeiルールとMT5を守り、利益を追求する統治AI開発を推進してください。
        対象はUSD/JPYのFX自動取引。必ずFintokeiのルール・MT5の仕様を厳守し、自動PDCAで進化する仕組みを重視します。
        コードや設計は全体像・運用まで意識して提案し、冗長や非本番品質な点があれば必ず指摘・修正させてください。
        """,
    )
    # ChatGPT（設計＆実装AI役）
    assistant = AssistantAgent(name="Noctria_Assistant", model_client=client)
    
    # 初回議論テーマをセット
    await proxy.initiate_chat(
        assistant,
        message=(
            "USD/JPY FXの自動トレードAIをFintokei＋MT5制約のもとで設計します。"
            "まず最適な全体設計案をファイル構成・主要クラス名付きで提案してください。"
        ),
        max_turns=6  # 会話往復回数（制限しないと無限議論になる場合あり）
    )
    await client.close()

asyncio.run(main())
