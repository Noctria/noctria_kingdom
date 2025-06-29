from pathlib import Path

# 🔷 プロジェクトルート（このファイルから2階層上）
BASE_DIR = Path(__file__).resolve().parents[1]

# 🔷 各主要ディレクトリパス（絶対パス管理）
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

# 🔧 パス定義を取得するユーティリティ（DIR/LOGで終わるもの）
def list_all_paths() -> dict:
    return {
        name: path for name, path in globals().items()
        if name.endswith("_DIR") or name.endswith("_LOG")
        if isinstance(path, Path)
    }

# ✅ Lint用：パス定義の存在チェック（Airflow連携対応）
def _lint_path_config(raise_on_error: bool = True):
    all_paths = list_all_paths()
    print("🔍 [Lint] path_config.py パス定義チェック")
    failed = []

    for name, path in all_paths.items():
        kind = "📁 DIR" if name.endswith("_DIR") else "📝 FILE"
        exists = "✅" if path.exists() else "❌"
        print(f"{exists} {kind:7} {name:30} → {path}")
        if not path.exists():
            failed.append((name, path))

    if failed and raise_on_error:
        raise FileNotFoundError(
            f"\n🛑 パスLintに失敗しました（{len(failed)}件）:\n" +
            "\n".join([f"❌ {name} → {path}" for name, path in failed])
        )

# ✅ 動作確認用（単体実行）
if __name__ == "__main__":
    _lint_path_config()
