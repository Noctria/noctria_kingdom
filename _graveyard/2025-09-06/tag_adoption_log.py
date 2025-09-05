# scripts/tag_adoption_log.py

import json
from pathlib import Path

ADOPTION_LOG_DIR = Path("data/act_logs/veritas_adoptions")

def assign_tags(log: dict) -> list[str]:
    tags = []

    # 条件ベースのタグ付与ルール（必要に応じて調整可）
    win_rate = log.get("score", {}).get("win_rate", 0)
    max_dd = log.get("score", {}).get("max_drawdown", 100)

    if win_rate >= 60:
        tags.append("high_winrate")
    elif win_rate >= 50:
        tags.append("moderate_winrate")

    if max_dd <= 5:
        tags.append("low_drawdown")
    elif max_dd >= 20:
        tags.append("risky")

    if log.get("status") == "promoted":
        tags.append("adopted")

    return tags

def process_logs():
    for path in sorted(ADOPTION_LOG_DIR.glob("veritas_log_*.json")):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 自動タグ付与
        data["tags"] = assign_tags(data)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ タグ更新済: {path.name}")

if __name__ == "__main__":
    process_logs()
