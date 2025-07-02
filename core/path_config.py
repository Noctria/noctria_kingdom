import os
from pathlib import Path

# 🔗 環境変数からベースパス取得（Docker/WSL/ローカル開発を考慮）
BASE_DIR = Path(os.getenv("TARGET_PROJECT_ROOT", "/mnt/d/noctria-kingdom-main")).resolve()

# 📂 各ディレクトリ定義
DAGS_DIR = BASE_DIR / "airflow_docker" / "dags"
LOGS_DIR = BASE_DIR / "airflow_docker" / "logs"
PLUGINS_DIR = BASE_DIR / "airflow_docker" / "plugins"

SCRIPTS_DIR = BASE_DIR / "scripts"
CORE_DIR = BASE_DIR / "core"
STRATEGIES_DIR = BASE_DIR / "strategies"
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
INSTITUTIONS_DIR = BASE_DIR / "institutions"
VERITAS_DIR = BASE_DIR / "veritas"
TOOLS_DIR = BASE_DIR / "tools"
TESTS_DIR = BASE_DIR / "tests"

# 📝 ファイルパス
VERITAS_EVAL_LOG = LOGS_DIR / "veritas_eval_result.json"
USDJPY_CSV = LOGS_DIR / "USDJPY_M1_201501020805_202506161647.csv"

# 🌐 エクスポート（__all__でIDE補完対応）
__all__ = [
    "BASE_DIR", "DAGS_DIR", "LOGS_DIR", "PLUGINS_DIR",
    "SCRIPTS_DIR", "CORE_DIR", "STRATEGIES_DIR", "DATA_DIR",
    "MODELS_DIR", "INSTITUTIONS_DIR", "VERITAS_DIR",
    "TOOLS_DIR", "TESTS_DIR",
    "VERITAS_EVAL_LOG", "USDJPY_CSV"
]
