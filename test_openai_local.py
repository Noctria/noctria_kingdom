# test_openai_local.py
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8009/v1", api_key="dummy")
resp = client.chat.completions.create(
    model="llama3.1:8b-instruct-q4_K_M",
    messages=[
        {"role": "system", "content": "あなたはNoctria王の執政AI。簡潔・実務優先で答える。"},
        {"role": "user", "content": "自己紹介して"},
    ],
    max_tokens=256,
)
print(resp.choices[0].message)
