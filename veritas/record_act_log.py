#!/usr/bin/env python3
# coding: utf-8

"""
📜 Veritas - Actフェーズ記録スクリプト
採用された戦略の情報を公式記録（act_logs）として保存します。
"""

import json
from pathlib import Path
from datetime import datetime
import argparse

# ✅ 王国の地図を参照
from core.path_config import ACT_LOG_DIR, VERITAS_EVAL_LOG

# 🧠 採用記録エントリの構築
def build_adoption_record(strategy_name: str, reason: str, metrics: dict) -> dict:
    return {
        "strategy": strategy_name,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "reason": reason,
        "metrics": metrics,
    }

# 💾 採用記録を保存
def save_adoption_record(record: dict):
    ACT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = record["timestamp"].replace(":", "-")
    strategy_sanitized = record['strategy'].replace(".py", "").replace("/", "_")
    out_path = ACT_LOG_DIR / f"{timestamp}_{strategy_sanitized}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"🗂️ 採用記録を保存しました: {out_path}")
    print("📜 王国記録:『選ばれし戦略、その名を歴史に刻まん。』")

# 🧠 veritas_eval_result.json を読み込み、最新の戦略を返す
def load_latest_eval_strategy() -> dict:
    if not VERITAS_EVAL_LOG.exists():
        raise FileNotFoundError(f"評価ログが見つかりません: {VERITAS_EVAL_LOG}")

    with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data or not isinstance(data, list):
        raise ValueError("評価結果が空または不正です")

    # 最新（最終）戦略を採用
    latest = data[-1]
    return {
        "strategy": latest.get("filename", "unknown_strategy.py"),
        "metrics": latest,
        "reason": "Veritas評価基準を満たしたため",
    }

# ✅ CLIインターフェース
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", type=str, help="採用された戦略名（例: my_strategy.py）")
    parser.add_argument("--reason", type=str, default="基準を満たしたため", help="採用理由")
    parser.add_argument("--metrics", type=str, help="評価指標のJSONファイルパス（省略可）")
    parser.add_argument("--auto", action="store_true", help="veritas_eval_result.json を自動取得")

    args = parser.parse_args()

    if args.auto:
        print("🧠 Veritas評価結果から最新の戦略を採用記録に反映します")
        try:
            latest = load_latest_eval_strategy()
            record = build_adoption_record(latest["strategy"], latest["reason"], latest["metrics"])
            save_adoption_record(record)
        except Exception as e:
            print(f"❌ 自動記録に失敗しました: {e}")
        return

    if not args.strategy:
        print("❌ --strategy を指定してください（または --auto を使用）")
        return

    metrics = {}
    if args.metrics:
        metrics_path = Path(args.metrics)
        if metrics_path.exists():
            with open(metrics_path, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        else:
            print(f"⚠️ 指定されたmetricsファイルが見つかりません: {metrics_path}")

    record = build_adoption_record(args.strategy, args.reason, metrics)
    save_adoption_record(record)

if __name__ == "__main__":
    main()
