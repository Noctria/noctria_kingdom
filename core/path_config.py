import os

# 🔗 環境変数からベースパス取得（Docker対応）
BASE_DIR = os.getenv("TARGET_PROJECT_ROOT", "/noctria_kingdom")

# 📂 各ディレクトリ定義（共通参照）
DAGS_DIR = os.path.join(BASE_DIR, "airflow_docker", "dags")
LOGS_DIR = os.path.join(BASE_DIR, "airflow_docker", "logs")
PLUGINS_DIR = os.path.join(BASE_DIR, "airflow_docker", "plugins")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
CORE_DIR = os.path.join(BASE_DIR, "core")
STRATEGIES_DIR = os.path.join(BASE_DIR, "strategies")
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
INSTITUTIONS_DIR = os.path.join(BASE_DIR, "institutions")
VERITAS_DIR = os.path.join(BASE_DIR, "veritas")
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
TESTS_DIR = os.path.join(BASE_DIR, "tests")

# 📝 ファイル単体パス
VERITAS_EVAL_LOG = os.path.join(LOGS_DIR, "veritas_eval_result.json")
USDJPY_CSV = os.path.join(LOGS_DIR, "USDJPY_M1_201501020805_202506161647.csv")
