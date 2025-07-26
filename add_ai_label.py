import os
import json

STATS_DIR = "data/stats"
AI_RULES = [
    ("veritas_", "Veritas"),
    ("aurus_", "Aurus"),
    ("levia_", "Levia"),
    ("noctus_", "Noctus"),
    ("prometheus_", "Prometheus"),
]

for fname in os.listdir(STATS_DIR):
    if not fname.endswith(".json"):
        continue
    path = os.path.join(STATS_DIR, fname)
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if "ai" in d:
        continue  # 既にaiがあるなら何もしない
    ai_name = "Unknown"
    strat = d.get("strategy", fname)
    for kw, ai in AI_RULES:
        if kw in strat.lower():
            ai_name = ai
            break
    d["ai"] = ai_name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"{fname}: ai={ai_name}")
