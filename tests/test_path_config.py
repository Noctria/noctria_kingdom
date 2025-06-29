# tests/test_path_config.py

import pytest
from core import path_config

@pytest.mark.parametrize("name", [
    "BASE_DIR",
    "AIRFLOW_DIR",
    "CORE_DIR",
    "VERITAS_DIR",
    "STRATEGIES_DIR",
    "OFFICIAL_STRATEGIES_DIR",
    "GENERATED_STRATEGIES_DIR",
    "EXECUTION_DIR",
    "DATA_DIR",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "FUNDAMENTAL_DATA_DIR",
    "MODELS_DIR",
    "LATEST_MODELS_DIR",
    "ARCHIVE_MODELS_DIR",
    "LLM_SERVER_DIR",
    "GUI_DIR",
    "EXPERTS_DIR",
    "TOOLS_DIR",
    "TESTS_DIR",
    "DOCS_DIR",
    "AIRFLOW_LOG_DIR",
    "VERITAS_EVAL_LOG"
])
def test_path_exists(name):
    """各パスがPathオブジェクトであることを検証"""
    value = getattr(path_config, name, None)
    assert value is not None, f"{name} is not defined"
    assert value.__class__.__name__ == "PosixPath" or value.__class__.__name__ == "WindowsPath", f"{name} is not a Path object"
