import json
import os
from datetime import datetime
from typing import Optional

TASK_STATUS_FILE = "task_status.json"

def load_task_status():
    if not os.path.exists(TASK_STATUS_FILE):
        return {}
    with open(TASK_STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_task_status(status_data):
    with open(TASK_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=2)

def update_task(file_name: str, status: str, comment: Optional[str] = None):
    data = load_task_status()
    now = datetime.utcnow().isoformat()
    if file_name not in data:
        data[file_name] = {"status": status, "last_updated": now, "comments": []}
    else:
        data[file_name]["status"] = status
        data[file_name]["last_updated"] = now
    if comment:
        data[file_name]["comments"].append(f"{now}: {comment}")
    save_task_status(data)

def get_task_status(file_name: str):
    data = load_task_status()
    return data.get(file_name, None)
