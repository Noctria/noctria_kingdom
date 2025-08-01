from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
import asyncio

async def main():
    client = OpenAIChatCompletionClient(model="gpt-4o")

    proxy = UserProxyAgent(name="Daifuku_Proxy")
    assistant = AssistantAgent(name="Noctria_Assistant", model_client=client)

    # UserProxyAgentにメッセージを送って会話開始
    user_message = "USD/JPY FXの自動トレードAIをFintokei＋MT5制約のもとで設計します。"

    # UserProxyAgentのsend_message()を使ってメッセージを送る
    response = await proxy.send_message(user_message, assistant)

    print("AI response:", response)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
