# tools/hardcoded_path_replacer.py

import re
from pathlib import Path

# パス変換ルール（文字列 → path_configの定数名）
REPLACEMENT_RULES = {
    r'["\']?/noctria_kingdom/airflow_docker/dags["\']?': "DAGS_DIR",
    r'["\']?/noctria_kingdom/airflow_docker/logs["\']?': "LOGS_DIR",
    r'["\']?/noctria_kingdom/airflow_docker/plugins["\']?': "PLUGINS_DIR",
    r'["\']?/noctria_kingdom/scripts["\']?': "SCRIPTS_DIR",
    r'["\']?/noctria_kingdom/core["\']?': "CORE_DIR",
    r'["\']?/noctria_kingdom/strategies["\']?': "STRATEGIES_DIR",
    r'["\']?/noctria_kingdom/data["\']?': "DATA_DIR",
    r'["\']?/noctria_kingdom/models["\']?': "MODELS_DIR",
    r'["\']?/noctria_kingdom/institutions["\']?': "INSTITUTIONS_DIR",
    r'["\']?/noctria_kingdom/veritas["\']?': "VERITAS_DIR",
    r'["\']?/noctria_kingdom/tools["\']?': "TOOLS_DIR",
    r'["\']?/noctria_kingdom/tests["\']?': "TESTS_DIR",
}

def replace_paths(file_path: Path):
    """ファイル内のハードコードされたパスを path_config 定数に置換する"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    replaced = False
    for pattern, const in REPLACEMENT_RULES.items():
        if re.search(pattern, content):
            content = re.sub(pattern, const, content)
            replaced = True

    if replaced:
        # 既に import 済みか確認
        if "from core.path_config import" not in content:
            content = f"from core.path_config import *\n\n{content}"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
