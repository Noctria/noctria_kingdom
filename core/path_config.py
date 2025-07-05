from pathlib import Path

# ========================================
# 📌 Noctria Kingdom Path Config (v3.4+)
#    - 全構成要素を王の地図に記録
#    - Docker/WSL/Local対応（自動切り替え）
# ========================================

# ✅ BASE_DIR の自動切り替え（Docker vs ローカル）
if Path("/opt/airflow").exists():
    BASE_DIR = Path("/opt/airflow").resolve()
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

# ========================================
# 🏛 中枢構成（Airflow/DAG/Pluginsなど）
# ========================================
DAGS_DIR = BASE_DIR / "airflow_docker" / "dags"
LOGS_DIR = BASE_DIR / "airflow_docker" / "logs"
PLUGINS_DIR = BASE_DIR / "airflow_docker" / "plugins"
AIRFLOW_SCRIPTS_DIR = BASE_DIR / "airflow_docker" / "scripts"
TOOLS_DIR = BASE_DIR / "tools"

# ========================================
# 🧠 知性領域（AI・戦略・評価）
# ========================================
CORE_DIR = BASE_DIR / "core"
SCRIPTS_DIR = BASE_DIR / "scripts"
VERITAS_DIR = BASE_DIR / "veritas"
STRATEGIES_DIR = BASE_DIR / "strategies"
EXECUTION_DIR = BASE_DIR / "execution"
EXPERTS_DIR = BASE_DIR / "experts"

# ========================================
# 📦 データ・モデル領域
# ========================================
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = BASE_DIR / "models"
INSTITUTIONS_DIR = BASE_DIR / "institutions"

# ========================================
# 🌐 GUI・推論サーバ・文書など
# ========================================
NOCTRIA_GUI_DIR = BASE_DIR / "noctria_gui"
NOCTRIA_GUI_TEMPLATES_DIR = NOCTRIA_GUI_DIR / "templates"
NOCTRIA_GUI_STATIC_DIR = NOCTRIA_GUI_DIR / "static"
GUI_TEMPLATES_DIR = NOCTRIA_GUI_TEMPLATES_DIR  # alias
GUI_STATIC_DIR = NOCTRIA_GUI_STATIC_DIR        # alias
GUI_ROUTES_DIR = NOCTRIA_GUI_DIR / "routes"
GUI_SERVICES_DIR = NOCTRIA_GUI_DIR / "services"

LLM_SERVER_DIR = BASE_DIR / "llm_server"
DOCS_DIR = BASE_DIR / "docs"
TESTS_DIR = BASE_DIR / "tests"

# ========================================
# 📄 ファイルパス（王国の記録物）
# ========================================
VERITAS_EVAL_LOG = LOGS_DIR / "veritas_eval_result.json"
USDJPY_CSV = LOGS_DIR / "USDJPY_M1_201501020805_202506161647.csv"
MARKET_DATA_CSV = DATA_DIR / "preprocessed_usdjpy_with_fundamental.csv"

# ✅ EA命令JSON保存先（環境によって変更可能）
if Path("/mnt/c/Users/masay/AppData/Roaming/MetaQuotes").exists():
    VERITAS_ORDER_JSON = Path(
        "/mnt/c/Users/masay/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files/veritas_signal.json"
    )
else:
    VERITAS_ORDER_JSON = BASE_DIR / "tmp" / "veritas_signal.json"

# ✅ PDCA履歴ログ保存用ディレクトリ
PDCA_LOG_DIR = DATA_DIR / "pdca_logs" / "veritas_orders"

# ========================================
# 🧠 Veritas関連スクリプト
# ========================================
VERITAS_GENERATE_SCRIPT = VERITAS_DIR / "generate_strategy_file.py"
VERITAS_EVALUATE_SCRIPT = VERITAS_DIR / "evaluate_veritas.py"
GENERATE_ORDER_SCRIPT = EXECUTION_DIR / "generate_order_json.py"

# ========================================
# 🔁 GitHub操作スクリプト
# ========================================
GITHUB_PUSH_SCRIPT = SCRIPTS_DIR / "github_push.py"

# ========================================
# 🗂 カテゴリ分類マップ（戦略ジャンル）
# ========================================
CATEGORY_MAP = {
    "technical": "📈 テクニカル分析",
    "fundamental": "📰 ファンダメンタル分析",
    "sentiment": "📊 センチメント分析",
    "reinforcement": "🤖 強化学習",
    "hybrid": "⚔️ ハイブリッド戦略",
    "experimental": "🧪 実験戦略",
    "legacy": "📜 旧版戦略"
}

# ========================================
# 🔍 パス整合性チェック関数（審査用）
# ========================================
def _lint_path_config():
    return {k: v.exists() for k, v in globals().items() if isinstance(v, Path)}

# ========================================
# 🌐 公開変数一覧（王の地図）
# ========================================
__all__ = [
    "BASE_DIR", "DAGS_DIR", "LOGS_DIR", "PLUGINS_DIR", "AIRFLOW_SCRIPTS_DIR",
    "TOOLS_DIR", "SCRIPTS_DIR", "CORE_DIR", "VERITAS_DIR", "STRATEGIES_DIR",
    "EXECUTION_DIR", "EXPERTS_DIR", "DATA_DIR", "RAW_DATA_DIR", "PROCESSED_DATA_DIR",
    "MODELS_DIR", "INSTITUTIONS_DIR", "NOCTRIA_GUI_DIR", "GUI_TEMPLATES_DIR",
    "GUI_STATIC_DIR", "GUI_ROUTES_DIR", "GUI_SERVICES_DIR",
    "NOCTRIA_GUI_STATIC_DIR", "NOCTRIA_GUI_TEMPLATES_DIR",
    "LLM_SERVER_DIR", "DOCS_DIR", "TESTS_DIR",
    "VERITAS_EVAL_LOG", "USDJPY_CSV", "MARKET_DATA_CSV",
    "VERITAS_GENERATE_SCRIPT", "VERITAS_EVALUATE_SCRIPT", "GENERATE_ORDER_SCRIPT",
    "VERITAS_ORDER_JSON", "PDCA_LOG_DIR", "GITHUB_PUSH_SCRIPT",
    "CATEGORY_MAP", "_lint_path_config"
]
