#!/usr/bin/env python3
# coding: utf-8

"""
📌 Noctria Kingdom Path Config (v4.4)
- 王国全体のパス構造を一元管理します。
- Docker/WSL/ローカル環境の差異を吸収し、自動で切り替えます。
- プロジェクトルート直下の `src` ディレクトリ構成を前提とします。
"""

from pathlib import Path

# ========================================
# 🏰 基本ディレクトリ判定（Docker or ローカル）
# ========================================
PROJECT_ROOT = Path("/opt/airflow").resolve() if Path("/opt/airflow").exists() else Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

# ========================================
# 🏛️ Airflow構成領域
# ========================================
AIRFLOW_DOCKER_DIR = PROJECT_ROOT / "airflow_docker"
DAGS_DIR = AIRFLOW_DOCKER_DIR / "dags"
LOGS_DIR = AIRFLOW_DOCKER_DIR / "logs"
PLUGINS_DIR = AIRFLOW_DOCKER_DIR / "plugins"
AIRFLOW_SCRIPTS_DIR = AIRFLOW_DOCKER_DIR / "scripts"

# ========================================
# 🧠 知性領域（AI・戦略・評価・実行）
# ========================================
CORE_DIR = SRC_DIR / "core"
SCRIPTS_DIR = SRC_DIR / "scripts"
VERITAS_DIR = SRC_DIR / "veritas"
STRATEGIES_DIR = SRC_DIR / "strategies"
STRATEGIES_VERITAS_GENERATED_DIR = STRATEGIES_DIR / "veritas_generated"
EXECUTION_DIR = SRC_DIR / "execution"
EXPERTS_DIR = SRC_DIR / "experts"
NOCTRIA_AI_DIR = SRC_DIR / "noctria_ai"
TOOLS_DIR = SRC_DIR / "tools"

# ========================================
# 📦 データ・モデル・ログ領域
# ========================================
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
INSTITUTIONS_DIR = PROJECT_ROOT / "institutions"
PDCA_LOG_DIR = DATA_DIR / "pdca_logs" / "veritas_orders"
ACT_LOG_DIR = DATA_DIR / "act_logs" / "veritas_adoptions"
PUSH_LOG_DIR = DATA_DIR / "push_logs"
ORACLE_FORECAST_JSON = DATA_DIR / "oracle" / "forecast.json"

# ========================================
# 🌐 GUI・推論サーバ・文書
# ========================================
NOCTRIA_GUI_DIR = PROJECT_ROOT / "noctria_gui"
NOCTRIA_GUI_TEMPLATES_DIR = NOCTRIA_GUI_DIR / "templates"
NOCTRIA_GUI_STATIC_DIR = NOCTRIA_GUI_DIR / "static"
NOCTRIA_GUI_ROUTES_DIR = NOCTRIA_GUI_DIR / "routes"
NOCTRIA_GUI_SERVICES_DIR = NOCTRIA_GUI_DIR / "services"
LLM_SERVER_DIR = PROJECT_ROOT / "llm_server"
DOCS_DIR = PROJECT_ROOT / "docs"
TESTS_DIR = PROJECT_ROOT / "tests"

# ========================================
# 📄 主要ファイルパス（王国の記録物）
# ========================================
VERITAS_EVAL_LOG = LOGS_DIR / "veritas_eval_result.json"
MARKET_DATA_CSV = DATA_DIR / "preprocessed_usdjpy_with_fundamental.csv"
MT5_USER_PATH = Path("/mnt/c/Users/masay/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files")
if MT5_USER_PATH.exists():
    VERITAS_ORDER_JSON = MT5_USER_PATH / "veritas_signal.json"
else:
    TEMP_DIR = PROJECT_ROOT / "tmp"
    TEMP_DIR.mkdir(exist_ok=True)
    VERITAS_ORDER_JSON = TEMP_DIR / "veritas_signal.json"

# ========================================
# 🤖 主要スクリプトパス
# ========================================
VERITAS_GENERATE_SCRIPT = VERITAS_DIR / "veritas_generate_strategy.py"
VERITAS_EVALUATE_SCRIPT = VERITAS_DIR / "evaluate_veritas.py"
GITHUB_PUSH_SCRIPT = SCRIPTS_DIR / "github_push.py"

# ✅ 修正: 削除されていたGITHUB_REPO_URLの定義を再追加
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
    return {k: v.exists() for k, v in globals().items() if isinstance(v, Path) and not k.startswith("_")}

# ========================================
# 🌐 公開定数（王の地図として他モジュールに輸出）
# ========================================
__all__ = [
    "PROJECT_ROOT", "SRC_DIR",
    "DAGS_DIR", "LOGS_DIR", "PLUGINS_DIR", "AIRFLOW_SCRIPTS_DIR",
    "CORE_DIR", "SCRIPTS_DIR", "VERITAS_DIR", "STRATEGIES_DIR", "STRATEGIES_VERITAS_GENERATED_DIR",
    "EXECUTION_DIR", "EXPERTS_DIR", "NOCTRIA_AI_DIR", "TOOLS_DIR",
    "DATA_DIR", "RAW_DATA_DIR", "PROCESSED_DATA_DIR", "MODELS_DIR", "INSTITUTIONS_DIR",
    "PDCA_LOG_DIR", "ACT_LOG_DIR", "PUSH_LOG_DIR", "ORACLE_FORECAST_JSON",
    "NOCTRIA_GUI_DIR", "NOCTRIA_GUI_TEMPLATES_DIR", "NOCTRIA_GUI_STATIC_DIR",
    "NOCTRIA_GUI_ROUTES_DIR", "NOCTRIA_GUI_SERVICES_DIR", "LLM_SERVER_DIR", "DOCS_DIR", "TESTS_DIR",
    "VERITAS_EVAL_LOG", "MARKET_DATA_CSV", "VERITAS_ORDER_JSON",
    "VERITAS_GENERATE_SCRIPT", "VERITAS_EVALUATE_SCRIPT", "GITHUB_PUSH_SCRIPT",
    "GITHUB_REPO_URL", "CATEGORY_MAP", "_lint_path_config"
]
