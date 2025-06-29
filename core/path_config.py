# core/path_config.py

from pathlib import Path

# 🔷 プロジェクトルート（このファイルから2階層上）
BASE_DIR = Path(__file__).resolve().parents[1]

# 🔷 各主要ディレクトリパス（原則：絶対パス）
AIRFLOW_DIR = BASE_DIR / "airflow_docker"
CORE_DIR = BASE_DIR / "core"
VERITAS_DIR = BASE_DIR / "veritas"
STRATEGIES_DIR = BASE_DIR / "strategies"
OFFICIAL_STRATEGIES_DIR = STRATEGIES_DIR / "official"
GENERATED_STRATEGIES_DIR = STRATEGIES_DIR / "veritas_generated"
EXECUTION_DIR = BASE_DIR / "execution"
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
FUNDAMENTAL_DATA_DIR = DATA_DIR / "fundamental"
MODELS_DIR = BASE_DIR / "models"
LATEST_MODELS_DIR = MODELS_DIR / "latest"
ARCHIVE_MODELS_DIR = MODELS_DIR / "archive"
LLM_SERVER_DIR = BASE_DIR / "llm_server"
GUI_DIR = BASE_DIR / "noctria_gui"
EXPERTS_DIR = BASE_DIR / "experts"
TOOLS_DIR = BASE_DIR / "tools"
TESTS_DIR = BASE_DIR / "tests"
DOCS_DIR = BASE_DIR / "docs"

# 🔷 Airflowログ
AIRFLOW_LOG_DIR = AIRFLOW_DIR / "logs"
VERITAS_EVAL_LOG = AIRFLOW_LOG_DIR / "veritas_eval_result.json"

# ✅ 動作確認用（オプション）
if __name__ == "__main__":
    for name, path in globals().items():
        if name.endswith("_DIR") or name.endswith("_LOG"):
            print(f"{name:30} → {path}")
