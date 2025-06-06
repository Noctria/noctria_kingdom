import os
import pandas as pd
import torch
import logging
from strategies.reinforcement.dqn_agent import DQNAgent
from core.NoctriaMasterAI import NoctriaMasterAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def find_best_model(metadata_path="logs/models/metadata.json"):
    if not os.path.exists(metadata_path):
        logging.warning("⚠️ メタデータがありません")
        return None
    df = pd.read_json(metadata_path, lines=True)
    if df.empty:
        logging.warning("⚠️ メタデータが空です")
        return None
    best_model_info = df.loc[df["win_rate"].idxmax()]
    return best_model_info["model_path"]

def switch_model(model_path):
    if not os.path.exists(model_path):
        logging.error(f"❌ モデルが見つかりません: {model_path}")
        return False
    try:
        noctria_ai = NoctriaMasterAI()
        noctria_ai.dqn_agent.model.load_state_dict(torch.load(model_path))
        noctria_ai.dqn_agent.model.eval()
        logging.info(f"✅ ベストモデルロード完了: {model_path}")
        return True
    except Exception as e:
        logging.error(f"❌ モデルロード失敗: {e}")
        return False

if __name__ == "__main__":
    logging.info("=== モデル自動切り替え開始 ===")
    best_model_path = find_best_model()
    if best_model_path:
        success = switch_model(best_model_path)
        if success:
            logging.info("🎉 切り替え完了！")
        else:
            logging.warning("⚠️ 切り替え失敗")
    else:
        logging.warning("⚠️ ベストモデルが見つかりません")
    logging.info("=== スクリプト終了 ===")
