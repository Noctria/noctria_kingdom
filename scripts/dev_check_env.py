import os
from pathlib import Path

from dotenv import load_dotenv

# プロジェクトルートにある .env を明示パス指定で読む（AssertionError回避）
root = Path(__file__).resolve().parents[1]
env_path = root / ".env"
load_dotenv(dotenv_path=env_path)

keys = [
    "OPENAI_API_KEY",
    "OPENAI_API_BASE",
    "OPENAI_BASE_URL",
    "NOCTRIA_GPT_MODEL",
    "OPENAI_MODEL",
    "NOCTRIA_LLM_ENABLED",
    "NOCTRIA_HARMONIA_MODE",
    "NOCTRIA_HERMES_ENABLED",
    "NOCTRIA_PLAN_TARGET_PROFIT",
]


def mask(v: str | None) -> str:
    if not v:
        return "None"
    if len(v) <= 8:
        return "*" * len(v)
    return v[:4] + "*" * (len(v) - 8) + v[-4:]


print("ENV file:", str(env_path))
for k in keys:
    v = os.getenv(k)
    if k.endswith("_KEY"):
        print(f"{k} = {mask(v)}")
    else:
        print(f"{k} = {v!r}")

# 代表的な“未設定”臭の判定
bad = []
if os.getenv("OPENAI_API_KEY") in (None, "", "REPLACE_ME", "sk-xxxx"):
    bad.append("OPENAI_API_KEY")
model = os.getenv("NOCTRIA_GPT_MODEL") or os.getenv("OPENAI_MODEL")
if model in (None, "", "REPLACE_ME"):
    bad.append("NOCTRIA_GPT_MODEL/OPENAI_MODEL")
if os.getenv("NOCTRIA_LLM_ENABLED") not in ("true", "True", "1", "on", "auto"):
    print("NOTE: NOCTRIA_LLM_ENABLED が off っぽい。auto or true を推奨。")

if bad:
    print("\n!! 要修正:", ", ".join(bad))
else:
    print("\nOK: 必須値は形の上では埋まっています。")
