import requests
import json

url = "http://host.docker.internal:11434/api/generate"

payload = {
    "model": "openhermes",
    "prompt": "あなたはFX戦略の専門家AIです。USDJPYの戦略案を3つ、簡潔に日本語で出力してください。",
    "stream": False
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    data = response.json()
    print("🧠 Veritas 応答:")
    print(data.get("response", "（応答なし）"))
else:
    print(f"⚠️ エラー {response.status_code}: {response.text}")
