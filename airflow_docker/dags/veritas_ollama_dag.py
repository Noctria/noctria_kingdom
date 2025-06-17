import os
import requests

# 🔧 環境変数から設定を取得
ollama_host = os.getenv("OLLAMA_HOST", "localhost")
ollama_port = os.getenv("OLLAMA_PORT", "11434")
ollama_model = os.getenv("OLLAMA_MODEL", "openhermes")
ollama_prompt = os.getenv("OLLAMA_PROMPT", "次のUSDJPY戦略を5つ考えてください。")

# 🌐 API URLを組み立て
url = f"http://{ollama_host}:{ollama_port}/api/generate"

# 📦 リクエスト送信
payload = {
    "model": ollama_model,
    "prompt": ollama_prompt
}

print(f"▶️ リクエスト送信先: {url}")
response = requests.post(url, json=payload, timeout=20)

# ✅ 結果出力
print("✅ 応答:", response.json())
