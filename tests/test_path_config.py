# tests/test_path_config.py

from core import path_config

print("🔍 Testing path_config.py paths...\n")

# ✅ テスト対象キーを限定（全部出すと多くて処理が止まる場合がある）
test_keys = [
    "BASE_DIR",
    "DATA_DIR",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "AIRFLOW_DIR",
    "AIRFLOW_LOG_DIR",
    "STRATEGIES_DIR",
    "GENERATED_STRATEGIES_DIR",
    "OFFICIAL_STRATEGIES_DIR",
    "LLM_SERVER_DIR",
]

for key in test_keys:
    if hasattr(path_config, key):
        print(f"{key:30} → {getattr(path_config, key)}")
    else:
        print(f"❌ {key} is missing in path_config.py")
