# scripts/log_pdca_result.py
import json
from datetime import datetime
from core.path_config import LOGS_DIR

PDCA_LOG_PATH = LOGS_DIR / "pdca_history.json"

def log_pdca_step(phase: str, status: str, detail: str = ""):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "phase": phase,
        "status": status,
        "detail": detail
    }

    if PDCA_LOG_PATH.exists():
        with open(PDCA_LOG_PATH, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(log_entry)

    with open(PDCA_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
