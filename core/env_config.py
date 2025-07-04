# =========================================
# 🔐 環境変数ローダー：Noctria Kingdom v3.0
# 説明: プロジェクト全体で使用される .env / .env.secret を統一して読み込む
# 使用例: from core.env_config import GITHUB_USERNAME, MODEL_DIR
# =========================================

import os
from pathlib import Path
from dotenv import load_dotenv

# ✅ 優先順位: .env.secret > .env
env_paths = [
    Path("/opt/airflow/.env.secret"),
    Path("/opt/airflow/.env"),
]

for path in env_paths:
    if path.exists():
        load_dotenv(dotenv_path=path, override=True)

# ==========================
# 🧠 読み込む環境変数（必要に応じて追加）
# ==========================

# GitHub連携
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "Noctria")
GITHUB_REPO = os.getenv("GITHUB_REPO", "noctria_kingdom")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # 🔐 None許容。存在チェックは使用側で行う

# モデル保存パス
MODEL_DIR = os.getenv("MODEL_DIR", "/opt/airflow/models/nous-hermes-2")

# LLM推論API
LLM_API_HOST = os.getenv("LLM_API_HOST", "localhost")
LLM_API_PORT = int(os.getenv("LLM_API_PORT", 11434))

# OpenAI等のAPIキー（必要なら）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# PostgreSQL（参考用）
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
