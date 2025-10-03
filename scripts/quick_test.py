from openai import OpenAI
c = OpenAI(base_url="http://127.0.0.1:8012/v1", api_key="noctria-secret")
r = c.chat.completions.create(
    model="noctria-king:latest",
    messages=[{"role":"user","content":"Airflow DAG健全性チェック。規定テンプレで1件、テンプレのみ。"}],
)
print(r.choices[0].message.content)
