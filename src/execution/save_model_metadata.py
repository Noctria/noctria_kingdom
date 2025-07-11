import json
import os
from datetime import datetime

def save_model_metadata(model_path, episode, total_reward, win_rate, extra_info=None):
    metadata = {
        "model_path": model_path,
        "episode": episode,
        "total_reward": total_reward,
        "win_rate": win_rate,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    if extra_info:
        metadata.update(extra_info)
    os.makedirs(os.path.dirname("logs/models/metadata.json"), exist_ok=True)
    with open("logs/models/metadata.json", "a") as f:
        f.write(json.dumps(metadata) + "\n")
    print(f"✅ メタデータ保存: {model_path}")
