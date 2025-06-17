import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "openhermes",
        "prompt": "Noctria Kingdomの戦略生成AI Veritas_Machinaとして、今週の為替市場における取引戦略を1つ提案してください。"
    }
)

print(response.json()["response"])
