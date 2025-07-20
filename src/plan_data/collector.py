# src/plan_data/collector.py
import os
import json
from pathlib import Path

class PlanDataCollector:
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir)

    def collect_act_logs(self):
        """Actログ（採用履歴）の全件ロード"""
        log_dir = self.base_dir / "pdca_logs" / "veritas_orders"
        records = []
        for path in log_dir.glob("*.json"):
            with open(path, encoding="utf-8") as f:
                try:
                    records.append(json.load(f))
                except Exception as e:
                    print(f"Log読み込み失敗: {path}: {e}")
        return records

    def collect_eval_results(self):
        """評価結果のロード（リスト or 辞書）"""
        eval_path = self.base_dir / "stats" / "veritas_eval_result.json"
        if eval_path.exists():
            with open(eval_path, encoding="utf-8") as f:
                return json.load(f)
        return []

    # 必要に応じて「市場データ」「タグ統計」なども拡張

    def collect_all(self):
        """PDCA-Planで必要な全データをまとめて返す"""
        return {
            "act_logs": self.collect_act_logs(),
            "eval_results": self.collect_eval_results(),
            # "market": ...
            # "tags": ...
        }

