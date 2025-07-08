#!/usr/bin/env python3
# coding: utf-8

"""
📁 ACT_LOG_DIR にダミー昇格ログファイルを10件生成
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from core.path_config import ACT_LOG_DIR

# 確保されたログ保存先
output_dir = Path(ACT_LOG_DIR)
output_dir.mkdir(parents=True, exist_ok=True)

# タグ候補
tag_pool = ["trend", "momentum", "mean_reversion", "breakout", "volatility"]

# ダミー10件作成
for i in range(10):
    log_date = (datetime.today() - timedelta(days=i)).strftime("%Y-%m-%d")
    status = "promoted" if i % 2 == 0 else "rejected"
    pushed = random.choice([True, False])
    pdca = f"pdca-cycle-{i}" if i % 3 == 0 else None

    data = {
        "date": log_date,
        "strategy_name": f"strategy_{i}",
        "status": status,
        "pushed_to_github": pushed,
        "pdca_cycle": pdca,
        "tags": random.sample(tag_pool, k=random.randint(1, 3)),
        "score": {
            "win_rate": round(random.uniform(40, 75), 1),
            "max_drawdown": round(random.uniform(5, 20), 1)
        }
    }

    file_path = output_dir / f"veritas_log_{log_date}_{i}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ ダミーログ10件作成完了: {output_dir}")
