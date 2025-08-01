import asyncio
import os
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core._message_context import UserMessage

load_dotenv()

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEYが設定されていません。")

    client = OpenAIChatCompletionClient(model="gpt-4o", api_key=api_key)

    assistant = AssistantAgent(
        name="Noctria_Assistant",
        system_message="FX自動トレードAIの設計を支援してください。",
        model_client=client,
    )

    user_message = "USD/JPYの自動トレードAIの設計を提案してください。"

    response = await assistant._model_client.create(
        messages=[UserMessage(content=user_message)]
    )
    print("AI response:", response.choices[0].message.content)

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
