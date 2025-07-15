from pathlib import Path
import json
from datetime import datetime
from src.core.path_config import PUSH_LOG_DIR

def load_push_logs(sort: str = "desc") -> list:
    logs = []
    if not PUSH_LOG_DIR.exists():
        return logs

    for file in sorted(PUSH_LOG_DIR.glob("*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["filename"] = file.name
                data["datetime"] = datetime.fromisoformat(data["pushed_at"])
                logs.append(data)
        except Exception as e:
            print(f"❌ ログ読み込み失敗: {file.name} ({e})")

    logs.sort(key=lambda x: x["datetime"], reverse=(sort != "asc"))
    return logs
