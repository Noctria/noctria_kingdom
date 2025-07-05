from pathlib import Path
import json
from collections import Counter
from datetime import datetime
from core.path_config import DATA_DIR

PUSH_LOG_DIR = DATA_DIR / "push_logs"

def load_push_logs():
    logs = []
    for file in sorted(PUSH_LOG_DIR.glob("*.json")):
        with open(file, "r", encoding="utf-8") as f:
            logs.append(json.load(f))
    return logs

def get_push_statistics():
    logs = load_push_logs()
    if not logs:
        return {
            "total_pushes": 0,
            "last_push_time": None,
            "unique_strategies": 0,
            "branch_counter": {},
        }

    total = len(logs)
    last_push_time = max(log["timestamp"] for log in logs)
    unique_strategies = len(set(log["strategy"] for log in logs))
    branches = Counter(log["branch"] for log in logs)

    return {
        "total_pushes": total,
        "last_push_time": last_push_time,
        "unique_strategies": unique_strategies,
        "branch_counter": branches,
    }
