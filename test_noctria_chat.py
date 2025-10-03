from openai import OpenAI

# OpenAIクライアントを初期化
client = OpenAI()

# ChatCompletionをリクエスト
resp = client.chat.completions.create(
    model="llama3.1:8b-instruct-q4_K_M",
    messages=[
        {"role": "system", "content": "あなたはNoctria王。実務優先で答える。"},
        {"role": "user", "content": "今日の優先タスクを3つ、理由と所要時間付きで。"},
    ],
    temperature=0.6,
    max_tokens=512,
)

print(resp.choices[0].message)
