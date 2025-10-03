import os
import sys
from pathlib import Path

from dotenv import load_dotenv

root = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=root / ".env")

# 環境から設定
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL")
model = os.getenv("NOCTRIA_GPT_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

if not api_key or api_key in ("REPLACE_ME", "sk-xxxx"):
    print("ERROR: OPENAI_API_KEY が未設定です。")
    sys.exit(2)

# OpenAI v1 クライアント
try:
    from openai import OpenAI
except Exception as e:
    print("openai パッケージが見当たりません。`pip install openai` を実行してください。")
    raise

kwargs = {"api_key": api_key}
if base_url:
    # 互換API（OpenRouter/Azure互換ゲートウェイ等）を使う場合用
    kwargs["base_url"] = base_url

client = OpenAI(**kwargs)

# 1) モデル一覧（権限・疎通確認）
try:
    _ = client.models.list()
    print("✓ models.list() OK")
except Exception as e:
    print("× models.list() NG:", e)

# 2) 低トークンの最小チャット（usage増分の実験）
try:
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say 'pong'."}],
        max_tokens=5,
        temperature=0,
    )
    content = r.choices[0].message.content
    usage = getattr(r, "usage", None)
    print("✓ chat OK:", content)
    if usage:
        print(
            f"usage: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}"
        )
    else:
        print("usage: providerが返していません（互換APIの可能性）")
except Exception as e:
    print("× chat NG:", e)
    sys.exit(3)
