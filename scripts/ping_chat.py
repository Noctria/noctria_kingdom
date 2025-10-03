# scripts/ping_chat.py
from openai import OpenAI
client = OpenAI(base_url="http://127.0.0.1:8009/v1", api_key="dummy")
r = client.chat.completions.create(
    model="llama3.1:8b-instruct-q4_K_M",
    messages=[{"role":"user","content":"Noctria王、今日やるべきことを1つだけ教えて"}],
    max_tokens=200,
)
print(r.choices[0].message.content)
