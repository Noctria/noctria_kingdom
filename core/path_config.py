from pathlib import Path

<<<<<<< HEAD
BASE_DIR = Path(__file__).resolve().parent.parent

PATHS = {
    "airflow_docker": BASE_DIR / "airflow_docker",
    "execution": BASE_DIR / "execution",
    "experts": BASE_DIR / "experts",
    "llm_server": BASE_DIR / "llm_server",
    "logs": BASE_DIR / "logs",
    "noctria_gui": BASE_DIR / "noctria_gui",
    "tests": BASE_DIR / "tests",
    "tools": BASE_DIR / "tools",
    "veritas": BASE_DIR / "veritas",
    "system_start": BASE_DIR / "system_start",
}
=======
# ========================================
# 📌 Noctria Kingdom Path Config (v3.0)
#    - 自動で BASE_DIR を切り替える構成
# ========================================

# ✅ BASE_DIR の自動切り替え
if Path("/opt/airflow").exists():
    # Docker / 本番環境
    BASE_DIR = Path("/opt/airflow").resolve()
else:
    # ローカル / 開発環境（WSL等）
    BASE_DIR = Path(__file__).resolve().parent.parent

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

# 📁 データサブディレクトリ
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# 📝 ファイルパス
VERITAS_EVAL_LOG = LOGS_DIR / "veritas_eval_result.json"
USDJPY_CSV = LOGS_DIR / "USDJPY_M1_201501020805_202506161647.csv"

# ✅ Veritas戦略生成スクリプトのパス（veritas/generate_strategy_file.py）
VERITAS_GENERATE_SCRIPT = VERITAS_DIR / "generate_strategy_file.py"

# ✅ パス整合性チェック関数（任意でDAGやテストから呼べる）
def _lint_path_config():
    return {
        "BASE_DIR": BASE_DIR.exists(),
        "DAGS_DIR": DAGS_DIR.exists(),
        "LOGS_DIR": LOGS_DIR.exists(),
        "STRATEGIES_DIR": STRATEGIES_DIR.exists(),
        "VERITAS_EVAL_LOG": VERITAS_EVAL_LOG.exists(),
        "RAW_DATA_DIR": RAW_DATA_DIR.exists(),
        "PROCESSED_DATA_DIR": PROCESSED_DATA_DIR.exists(),
        "VERITAS_GENERATE_SCRIPT": VERITAS_GENERATE_SCRIPT.exists(),
    }

# 🌐 公開変数一覧（補完・明示用）
__all__ = [
    "BASE_DIR", "DAGS_DIR", "LOGS_DIR", "PLUGINS_DIR",
    "SCRIPTS_DIR", "CORE_DIR", "STRATEGIES_DIR", "DATA_DIR",
    "MODELS_DIR", "INSTITUTIONS_DIR", "VERITAS_DIR",
    "TOOLS_DIR", "TESTS_DIR",
    "RAW_DATA_DIR", "PROCESSED_DATA_DIR",
    "VERITAS_EVAL_LOG", "USDJPY_CSV",
    "VERITAS_GENERATE_SCRIPT",
    "_lint_path_config"
]
>>>>>>> 572191d22755722942baf299a92693377c177f7a
