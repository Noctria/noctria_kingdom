#!/usr/bin/env python3
# coding: utf-8
"""
📌 Noctria Kingdom Path Config (v5.1)

- 王国全体のパス構造を一元管理
- Docker/WSL/ローカル差異を吸収し、ENVで上書き可能
- 実行層リネーム（execution -> do）に互換レイヤで対応
- ✅ ensure_import_path(): エントリポイント側で呼べば import 経路を安定化
- ✅ NOCTRIA_AUTOPATH=1 で import 時に自動で sys.path を整備（任意）
- ✅ NEW: ensure_strategy_packages(): strategies 配下に __init__.py を自動整備
- ✅ NOCTRIA_AUTOINIT=1 で __init__.py を自動生成（任意）
"""

from __future__ import annotations

from pathlib import Path
import os
import sys
from contextlib import contextmanager

# =========================================================
# 🏰 基本ディレクトリ判定（Docker or ローカル）＋ENV上書き
# =========================================================
# 優先順位: ENV(NOCTRIA_PROJECT_ROOT) > /opt/airflow > 本ファイルからの相対
_env_root = os.getenv("NOCTRIA_PROJECT_ROOT")
if _env_root:
    PROJECT_ROOT = Path(_env_root).resolve()
else:
    PROJECT_ROOT = Path("/opt/airflow").resolve() if Path("/opt/airflow").exists() else Path(__file__).resolve().parents[2]

SRC_DIR = PROJECT_ROOT / "src"
BASE_DIR = PROJECT_ROOT  # 歴史的互換（BASE_DIR = プロジェクトルート）

# =========================================================
# 🏛️ Airflow構成領域
# =========================================================
AIRFLOW_DOCKER_DIR = PROJECT_ROOT / "airflow_docker"
DAGS_DIR = AIRFLOW_DOCKER_DIR / "dags"
LOGS_DIR = AIRFLOW_DOCKER_DIR / "logs"
PLUGINS_DIR = AIRFLOW_DOCKER_DIR / "plugins"
AIRFLOW_SCRIPTS_DIR = AIRFLOW_DOCKER_DIR / "scripts"

# =========================================================
# 🌐 Airflow APIベースURL（ENV上書き対応）
# =========================================================
AIRFLOW_API_BASE = os.getenv("AIRFLOW_API_BASE", "http://localhost:8080").rstrip("/")

# =========================================================
# 🧠 知性領域（AI・戦略・評価・実行）
# =========================================================
CORE_DIR = SRC_DIR / "core"
SCRIPTS_DIR = SRC_DIR / "scripts"
VERITAS_DIR = SRC_DIR / "veritas"
STRATEGIES_DIR = SRC_DIR / "strategies"
STRATEGIES_VERITAS_GENERATED_DIR = STRATEGIES_DIR / "veritas_generated"

# --- 実行層（将来 rename: execution → do）互換レイヤ ---
DO_DIR_CANDIDATE = SRC_DIR / "do"
EXECUTION_DIR_CANDIDATE = SRC_DIR / "execution"
DO_DIR = DO_DIR_CANDIDATE if DO_DIR_CANDIDATE.exists() else EXECUTION_DIR_CANDIDATE
EXECUTION_DIR = DO_DIR  # 旧名互換

# --- 専門領域・アダプタ等 ---
EXPERTS_DIR = (PROJECT_ROOT / "experts") if (PROJECT_ROOT / "experts").exists() else (SRC_DIR / "experts")
NOCTRIA_AI_DIR = SRC_DIR / "noctria_ai"
TOOLS_DIR = SRC_DIR / "tools"

# --- モデル/AI関連 ---
VERITAS_MODELS_DIR = VERITAS_DIR / "models"
HERMES_DIR = SRC_DIR / "hermes"
HERMES_MODELS_DIR = HERMES_DIR / "models"

# =========================================================
# 📦 データ・モデル・ログ領域
# =========================================================
DATA_DIR = PROJECT_ROOT / "data"
STATS_DIR = DATA_DIR / "stats"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

DATA_SOURCE_URL = os.getenv("DATA_SOURCE_URL", "https://example.com/data/source.csv")
LOCAL_DATA_PATH = DATA_DIR / "local_data"
FEATURES_PATH = PROCESSED_DATA_DIR / "features"
MODEL_PATH = DATA_DIR / "models" / "latest_model.pkl"

INSTITUTIONS_DIR = (AIRFLOW_DOCKER_DIR / "institutions") if (AIRFLOW_DOCKER_DIR / "institutions").exists() else PROJECT_ROOT / "institutions"

PDCA_LOG_DIR = DATA_DIR / "pdca_logs" / "veritas_orders"
ACT_LOG_DIR = DATA_DIR / "act_logs" / "veritas_adoptions"
PUSH_LOG_DIR = DATA_DIR / "push_logs"
ORACLE_FORECAST_JSON = DATA_DIR / "oracle" / "forecast.json"

# =========================================================
# 🌐 GUI・推論サーバ・文書
# =========================================================
NOCTRIA_GUI_DIR = PROJECT_ROOT / "noctria_gui"
NOCTRIA_GUI_TEMPLATES_DIR = NOCTRIA_GUI_DIR / "templates"
NOCTRIA_GUI_STATIC_DIR = NOCTRIA_GUI_DIR / "static"
NOCTRIA_GUI_ROUTES_DIR = NOCTRIA_GUI_DIR / "routes"
NOCTRIA_GUI_SERVICES_DIR = NOCTRIA_GUI_DIR / "services"
LLM_SERVER_DIR = PROJECT_ROOT / "llm_server"
DOCS_DIR = PROJECT_ROOT / "docs"
TESTS_DIR = PROJECT_ROOT / "tests"

# --- 互換性のためのエイリアス ---
GUI_TEMPLATES_DIR = NOCTRIA_GUI_TEMPLATES_DIR  # <--- 修正: エイリアスを追加

# =========================================================
# 📄 主要ファイルパス（王国の記録物）
# =========================================================
VERITAS_EVAL_LOG = LOGS_DIR / "veritas_eval_result.json"
MARKET_DATA_CSV = DATA_DIR / "preprocessed_usdjpy_with_fundamental.csv"

# Windows MT5ユーザパス（WSL/Windows混在対策）
MT5_USER_PATH = Path(
    os.getenv(
        "MT5_USER_PATH",
        "/mnt/c/Users/masay/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Files",
    )
)
if MT5_USER_PATH.exists():
    VERITAS_ORDER_JSON = MT5_USER_PATH / "veritas_signal.json"
else:
    TEMP_DIR = PROJECT_ROOT / "tmp"
    TEMP_DIR.mkdir(exist_ok=True)
    VERITAS_ORDER_JSON = TEMP_DIR / "veritas_signal.json"

# =========================================================
# 🤖 主要スクリプトパス（存在チェックつきフォールバック）
# =========================================================
VERITAS_GENERATE_SCRIPT = VERITAS_DIR / "veritas_generate_strategy.py"
VERITAS_EVALUATE_SCRIPT = VERITAS_DIR / "evaluate_veritas.py"

_github_push_primary = AIRFLOW_SCRIPTS_DIR / "github_push.py"
_github_push_fallback = SCRIPTS_DIR / "github_push.py"
_github_push_alt = SCRIPTS_DIR / "github_push_adopted_strategies.py"

if _github_push_primary.exists():
    GITHUB_PUSH_SCRIPT = _github_push_primary
elif _github_push_fallback.exists():
    GITHUB_PUSH_SCRIPT = _github_push_fallback
elif _github_push_alt.exists():
    GITHUB_PUSH_SCRIPT = _github_push_alt
else:
    GITHUB_PUSH_SCRIPT = _github_push_primary  # 未作成でも参照時に気づけるように

# 公開リポジトリURL（ENV上書き可能）
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "https://github.com/Noctria/noctria_kingdom")

# =========================================================
# 🗂 戦略カテゴリ分類マップ（GUI用）
# =========================================================
CATEGORY_MAP = {
    "technical": "📈 テクニカル分析",
    "fundamental": "📰 ファンダメンタル分析",
    "sentiment": "📊 センチメント分析",
    "reinforcement": "🤖 強化学習",
    "hybrid": "⚔️ ハイブリッド戦略",
    "experimental": "🧪 実験戦略",
    "legacy": "📜 旧版戦略",
}

# =========================================================
# ✅ パス整合性・import パス整備ユーティリティ
# =========================================================
def _lint_path_config():
    """各 Path が存在するかの簡易チェック（GUI/CLI デバッグ用）"""
    return {k: v.exists() for k, v in globals().items() if isinstance(v, Path) and not k.startswith("_")}


def _str(p: Path) -> str:
    return str(p.resolve())


def ensure_import_path(
    *,
    include_project_root: bool = True,
    include_src: bool = True,
    extra: tuple[Path, ...] | list[Path] = (),
) -> None:
    """
    sys.path を整備する共通関数。
    - エントリポイント（CLI/テスト/DAG/スクリプト）の冒頭で1回呼ぶだけで OK。
      例:
          from src.core.path_config import ensure_import_path
          ensure_import_path()    # 以降は 'from plan_data...','from decision...' が安定
    Args:
      include_project_root: repo ルートを import 経路に含める（'src.' 付き import 用）
      include_src:           'src' を import 経路に含める（トップレベル import 用）
      extra:                 追加したい Path（任意）
    """
    targets: list[str] = []
    if include_project_root:
        targets.append(_str(PROJECT_ROOT))
    if include_src:
        targets.append(_str(SRC_DIR))
    targets.extend(_str(p) for p in extra if isinstance(p, Path))

    # 先頭優先で追加（重複は追加しない）
    for t in reversed(targets):  # 末尾から insert(0) することで targets の先頭が最前列へ
        if t not in sys.path:
            sys.path.insert(0, t)


@contextmanager
def with_import_path(**kwargs):
    """ensure_import_path を一時的に適用するコンテキストマネージャ。"""
    before = list(sys.path)
    ensure_import_path(**kwargs)
    try:
        yield
    finally:
        sys.path[:] = before


# --- NEW: strategies パッケージの __init__.py を自動整備（任意） ---
def ensure_strategy_packages() -> None:
    """
    strategies 配下を import できるように __init__.py を自動整備する。
    - 生成・上書きはしない（存在しなければ最小内容で作成）
    """
    for d in (STRATEGIES_DIR, STRATEGIES_VERITAS_GENERATED_DIR):
        d.mkdir(parents=True, exist_ok=True)
        init_file = d / "__init__.py"
        if not init_file.exists():
            try:
                init_file.write_text("# package init (auto-created by path_config)\n", encoding="utf-8")
            except Exception:
                # 失敗しても致命ではない
                pass


# ENV で自動適用したい場合（明示 opt-in）
if os.getenv("NOCTRIA_AUTOPATH", "").lower() in {"1", "true", "yes"}:
    ensure_import_path()

if os.getenv("NOCTRIA_AUTOINIT", "").lower() in {"1", "true", "yes"}:
    ensure_strategy_packages()

# =========================================================
# 🌐 公開定数（王の地図として他モジュールに輸出）
# =========================================================
__all__ = [
    # ルート
    "PROJECT_ROOT", "SRC_DIR", "BASE_DIR",
    # Airflow
    "AIRFLOW_DOCKER_DIR", "DAGS_DIR", "LOGS_DIR", "PLUGINS_DIR", "AIRFLOW_SCRIPTS_DIR", "AIRFLOW_API_BASE",
    # コア/スクリプト/AI
    "CORE_DIR", "SCRIPTS_DIR", "VERITAS_DIR", "STRATEGIES_DIR", "STRATEGIES_VERITAS_GENERATED_DIR",
    # 実行層（新旧互換）
    "DO_DIR", "EXECUTION_DIR",
    # 周辺領域
    "EXPERTS_DIR", "NOCTRIA_AI_DIR", "TOOLS_DIR",
    # モデル/AI
    "VERITAS_MODELS_DIR", "HERMES_DIR", "HERMES_MODELS_DIR",
    # データ領域
    "DATA_DIR", "RAW_DATA_DIR", "PROCESSED_DATA_DIR", "STATS_DIR",
    "INSTITUTIONS_DIR",
    "PDCA_LOG_DIR", "ACT_LOG_DIR", "PUSH_LOG_DIR", "ORACLE_FORECAST_JSON",
    # GUI/Docs/Tests/LLM
    "NOCTRIA_GUI_DIR", "NOCTRIA_GUI_TEMPLATES_DIR", "NOCTRIA_GUI_STATIC_DIR",
    "NOCTRIA_GUI_ROUTES_DIR", "NOCTRIA_GUI_SERVICES_DIR",
    "GUI_TEMPLATES_DIR",  # <--- 修正: エイリアスを公開リストに追加
    "LLM_SERVER_DIR", "DOCS_DIR", "TESTS_DIR",
    # 主要ファイル
    "VERITAS_EVAL_LOG", "MARKET_DATA_CSV", "VERITAS_ORDER_JSON",
    # スクリプト/Repo
    "VERITAS_GENERATE_SCRIPT", "VERITAS_EVALUATE_SCRIPT", "GITHUB_PUSH_SCRIPT",
    "GITHUB_REPO_URL",
    # 分類
    "CATEGORY_MAP",
    # ユーティリティ
    "_lint_path_config",
    "ensure_import_path",
    "with_import_path",
    "ensure_strategy_packages",
]
