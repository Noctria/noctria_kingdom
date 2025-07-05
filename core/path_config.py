from pathlib import Path

# ========================================
# 📌 Noctria Kingdom Path Config (v3.0)
#    - 自動で BASE_DIR を切り替える構成
#    - すべての構成要素を王の地図に記録
# ========================================

# ✅ BASE_DIR の自動切り替え（Docker vs ローカル）
if Path("/opt/airflow").exists():
    # Docker / 本番環境
    BASE_DIR = Path("/opt/airflow").resolve()
else:
    # ローカル / 開発環境（WSL等）
    BASE_DIR = Path(__file__).resolve().parent.parent

# ========================================
# 🏛 ディレクトリ定義（王国の各領土）
# ========================================

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

# ✅ GUI構成（前線本部）
NOCTRIA_GUI_DIR = BASE_DIR / "noctria_gui"
GUI_TEMPLATES_DIR = NOCTRIA_GUI_DIR / "templates"

# ========================================
# 📂 サブディレクトリ（補佐官領域）
# ========================================

RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# ========================================
# 📄 ファイルパス（王国の記録物）
# ========================================

VERITAS_EVAL_LOG = LOGS_DIR / "veritas_eval_result.json"
USDJPY_CSV = LOGS_DIR / "USDJPY_M1_201501020805_202506161647.csv"
MARKET_DATA_CSV = DATA_DIR / "preprocessed_usdjpy_with_fundamental.csv"

# ========================================
# 🧠 Veritas関連スクリプト
# ========================================

VERITAS_GENERATE_SCRIPT = VERITAS_DIR / "generate_strategy_file.py"
VERITAS_EVALUATE_SCRIPT = VERITAS_DIR / "evaluate_veritas.py"

# ========================================
# 🛠 GitHub連携スクリプト
# ========================================

GITHUB_PUSH_SCRIPT = SCRIPTS_DIR / "github_push.py"

# ========================================
# 🔍 パス整合性チェック（審査用）
# ========================================

def _lint_path_config():
    return {
        "BASE_DIR": BASE_DIR.exists(),
        "DAGS_DIR": DAGS_DIR.exists(),
        "LOGS_DIR": LOGS_DIR.exists(),
        "STRATEGIES_DIR": STRATEGIES_DIR.exists(),
        "VERITAS_EVAL_LOG": VERITAS_EVAL_LOG.exists(),
        "RAW_DATA_DIR": RAW_DATA_DIR.exists(),
        "PROCESSED_DATA_DIR": PROCESSED_DATA_DIR.exists(),
        "MARKET_DATA_CSV": MARKET_DATA_CSV.exists(),
        "VERITAS_GENERATE_SCRIPT": VERITAS_GENERATE_SCRIPT.exists(),
        "VERITAS_EVALUATE_SCRIPT": VERITAS_EVALUATE_SCRIPT.exists(),
        "GITHUB_PUSH_SCRIPT": GITHUB_PUSH_SCRIPT.exists(),
        "NOCTRIA_GUI_DIR": NOCTRIA_GUI_DIR.exists(),
        "GUI_TEMPLATES_DIR": GUI_TEMPLATES_DIR.exists(),
    }

# ========================================
# 🌐 公開変数（王国全体地図）
# ========================================

__all__ = [
    "BASE_DIR", "DAGS_DIR", "LOGS_DIR", "PLUGINS_DIR",
    "SCRIPTS_DIR", "CORE_DIR", "STRATEGIES_DIR", "DATA_DIR",
    "MODELS_DIR", "INSTITUTIONS_DIR", "VERITAS_DIR",
    "TOOLS_DIR", "TESTS_DIR",
    "RAW_DATA_DIR", "PROCESSED_DATA_DIR",
    "VERITAS_EVAL_LOG", "USDJPY_CSV", "MARKET_DATA_CSV",
    "VERITAS_GENERATE_SCRIPT", "VERITAS_EVALUATE_SCRIPT",
    "GITHUB_PUSH_SCRIPT",
    "NOCTRIA_GUI_DIR", "GUI_TEMPLATES_DIR",
    "_lint_path_config"
]
