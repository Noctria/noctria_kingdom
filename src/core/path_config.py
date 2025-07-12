#!/usr/bin/env python3
# coding: utf-8

"""
📌 Noctria Kingdom Path Config (v4.0)
- 王国全体のパス構造を一元管理
- Docker/WSL/ローカルの差異を吸収し、自動で切り替える
- src/ 配下に統合された構成を前提とする
"""

from pathlib import Path

# ========================================
# 🏰 基本ディレクトリ判定（Docker or ローカル）
# ========================================
BASE_DIR = Path("/opt/airflow").resolve() if Path("/opt/airflow").exists() else Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR

SRC_DIR = BASE_DIR / "src"

# ========================================
# 🏛 Airflow構成領域
# ========================================
DAGS_DIR = BASE_DIR / "airflow_docker" / "dags"
LOGS_DIR = BASE_DIR / "airflow_docker" / "logs"
PLUGINS_DIR = BASE_DIR / "airflow_docker" / "plugins"
AIRFLOW_SCRIPTS_DIR = BASE_DIR / "airflow_docker" / "scripts"
TOOLS_DIR = BASE_DIR / "tools"

# ========================================
# 🧠 知性領域（AI・戦略・評価・実行）
# ========================================
CORE_DIR = SRC_DIR / "core"
SCRIPTS_DIR = SRC_DIR / "scripts"
VERITAS_DIR = SRC_DIR / "veritas"
STRATEGIES_DIR = SRC_DIR / "strategies"
EXECUTION_DIR = SRC_DIR / "execution"
EXPERTS_DIR = SRC_DIR / "experts"
NOCTRIA_AI_DIR = SRC_DIR / "noctria_ai"

# ========================================
# 📦 データ・モデル領域
# ========================================
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = BASE_DIR / "models"
INSTITUTIONS_DIR = BASE_DIR / "institutions"

# ========================================
# 🌐 GUI・推論サーバ・文書
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

# ✅ EA命令JSON出力先（環境に応じて切替）
if Path("/mnt/c/Users/masay/AppData/Roaming/MetaQuotes").exists():
    VERITAS_ORDER_JSON = Path(
        "/mnt/c/Users/masay/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files/veritas_signal.json"
    )
else:
    VERITAS_ORDER_JSON = BASE_DIR / "tmp" / "veritas_signal.json"

# ========================================
# 📜 ログ保存ディレクトリ（PDCA/昇格）
# ========================================
PDCA_LOG_DIR = DATA_DIR / "pdca_logs" / "veritas_orders"
ACT_LOG_DIR = DATA_DIR / "act_logs" / "veritas_adoptions"
PUSH_LOG_DIR = DATA_DIR / "push_logs"

# ========================================
# 🔮 Oracle予測結果保存先（将来活用用）
# ========================================
ORACLE_FORECAST_JSON = DATA_DIR / "oracle" / "forecast.json"

# ========================================
# 🧠 Veritas関連スクリプトパス
# ========================================
VERITAS_GENERATE_SCRIPT = VERITAS_DIR / "generate_strategy_file.py"
VERITAS_EVALUATE_SCRIPT = VERITAS_DIR / "evaluate_veritas.py"
GENERATE_ORDER_SCRIPT = EXECUTION_DIR / "generate_order_json.py"

# ========================================
# 🔁 GitHub関連設定
# ========================================
GITHUB_PUSH_SCRIPT = SCRIPTS_DIR / "github_push.py"
GITHUB_REPO_URL = "https://github.com/Noctria/noctria_kingdom"

# ========================================
# 🗂 戦略カテゴリ分類マップ（GUI用）
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
# ✅ パス整合性チェック用ユーティリティ
# ========================================
def _lint_path_config():
    return {k: v.exists() for k, v in globals().items() if isinstance(v, Path)}

# ========================================
# 🌐 公開定数（王の地図として他モジュールに輸出）
# ========================================
__all__ = [
    "BASE_DIR", "PROJECT_ROOT", "SRC_DIR",
    "DAGS_DIR", "LOGS_DIR", "PLUGINS_DIR", "AIRFLOW_SCRIPTS_DIR",
    "TOOLS_DIR", "SCRIPTS_DIR", "CORE_DIR", "VERITAS_DIR", "STRATEGIES_DIR",
    "EXECUTION_DIR", "EXPERTS_DIR", "NOCTRIA_AI_DIR",
    "DATA_DIR", "RAW_DATA_DIR", "PROCESSED_DATA_DIR",
    "MODELS_DIR", "INSTITUTIONS_DIR",
    "NOCTRIA_GUI_DIR", "NOCTRIA_GUI_TEMPLATES_DIR", "NOCTRIA_GUI_STATIC_DIR",
    "GUI_TEMPLATES_DIR", "GUI_STATIC_DIR", "GUI_ROUTES_DIR", "GUI_SERVICES_DIR",
    "LLM_SERVER_DIR", "DOCS_DIR", "TESTS_DIR",
    "VERITAS_EVAL_LOG", "USDJPY_CSV", "MARKET_DATA_CSV", "VERITAS_ORDER_JSON",
    "PDCA_LOG_DIR", "ACT_LOG_DIR", "PUSH_LOG_DIR",
    "ORACLE_FORECAST_JSON",
    "VERITAS_GENERATE_SCRIPT", "VERITAS_EVALUATE_SCRIPT", "GENERATE_ORDER_SCRIPT",
    "GITHUB_PUSH_SCRIPT", "GITHUB_REPO_URL", "CATEGORY_MAP",
    "_lint_path_config",
    # 追加した項目
    "STRATEGIES_VERITAS_GENERATED_DIR"
]

# ========================================
# 🧠 Veritas戦略保存ディレクトリ設定
# ========================================
STRATEGIES_VERITAS_GENERATED_DIR = BASE_DIR / "strategies" / "veritas_generated"
