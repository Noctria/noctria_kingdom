# core/path_config.py

from pathlib import Path

# 🔷 プロジェクトルート（このファイルから2階層上）
BASE_DIR = Path(__file__).resolve().parents[1]

# 🔷 各ディレクトリ・ファイルの集中定義
AIRFLOW_DIR               = BASE_DIR / "airflow_docker"
CORE_DIR                  = BASE_DIR / "core"
VERITAS_DIR               = BASE_DIR / "veritas"
STRATEGIES_DIR            = BASE_DIR / "strategies"
OFFICIAL_STRATEGIES_DIR   = STRATEGIES_DIR / "official"
GENERATED_STRATEGIES_DIR  = STRATEGIES_DIR / "veritas_generated"
EXECUTION_DIR             = BASE_DIR / "execution"
DATA_DIR                  = BASE_DIR / "data"
RAW_DATA_DIR              = DATA_DIR / "raw"
PROCESSED_DATA_DIR        = DATA_DIR / "processed"
FUNDAMENTAL_DATA_DIR      = DATA_DIR / "fundamental"
MODELS_DIR                = BASE_DIR / "models"
LATEST_MODELS_DIR         = MODELS_DIR / "latest"
ARCHIVE_MODELS_DIR        = MODELS_DIR / "archive"
LLM_SERVER_DIR            = BASE_DIR / "llm_server"
GUI_DIR                   = BASE_DIR / "noctria_gui"
EXPERTS_DIR               = BASE_DIR / "experts"
TOOLS_DIR                 = BASE_DIR / "tools"
TESTS_DIR                 = BASE_DIR / "tests"
DOCS_DIR                  = BASE_DIR / "docs"

# 🔷 ログ・ファイル系
AIRFLOW_LOG_DIR           = AIRFLOW_DIR / "logs"
VERITAS_EVAL_LOG          = AIRFLOW_LOG_DIR / "veritas_eval_result.json"

# 🔧 補助関数：すべてのパス定数を取得
def list_all_paths():
    return {
        k: v for k, v in globals().items()
        if isinstance(v, Path) and (k.endswith("_DIR") or k.endswith("_LOG") or k.endswith("_FILE"))
    }

# 🧪 簡易 Lint チェック機能
def _lint_path_config():
    all_paths = list_all_paths()
    print("🔍 [Lint] path_config.py パス定義チェック")
    for name, path in all_paths.items():
        kind = "📁 DIR" if name.endswith("_DIR") else "📝 FILE"
        exists = "✅" if path.exists() else "❌"
        print(f"{exists} {kind:7} {name:30} → {path}")

# ✅ 動作確認 / Lint 用
if __name__ == "__main__":
    _lint_path_config()
