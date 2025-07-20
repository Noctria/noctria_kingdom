# src/plan_data/collector.py

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

class PlanDataCollector:
    """
    PDCA-Plan策定用に各種ログ・評価・市場データを統合収集するコアクラス
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        base_dir: データディレクトリのルート（デフォルトはプロジェクト直下のdata/）
        """
        self.base_dir = Path(base_dir or "data")

    def collect_act_logs(self) -> List[Dict[str, Any]]:
        """
        Actログ（採用履歴）の全件ロード
        """
        log_dir = self.base_dir / "pdca_logs" / "veritas_orders"
        if not log_dir.exists():
            return []
        records = []
        for path in log_dir.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    data["_filename"] = path.name
                    records.append(data)
            except Exception as e:
                print(f"[collector] Actログ読み込み失敗: {path}: {e}")
        return records

    def collect_eval_results(self) -> List[Dict[str, Any]]:
        """
        評価結果（全戦略評価ログ）のロード
        """
        eval_path = self.base_dir / "stats" / "veritas_eval_result.json"
        if not eval_path.exists():
            return []
        try:
            with open(eval_path, encoding="utf-8") as f:
                data = json.load(f)
                # 1件のみでもリスト化して返す
                return data if isinstance(data, list) else [data]
        except Exception as e:
            print(f"[collector] 評価結果ログ読み込み失敗: {eval_path}: {e}")
            return []

    def collect_market_data(self) -> List[Dict[str, Any]]:
        """
        市場データ（必要に応じて拡張。今はダミー）
        """
        # 例: data/market/latest.json
        market_path = self.base_dir / "market" / "latest.json"
        if not market_path.exists():
            return []
        try:
            with open(market_path, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else [data]
        except Exception as e:
            print(f"[collector] 市場データ読み込み失敗: {market_path}: {e}")
            return []

    def collect_all(self) -> Dict[str, Any]:
        """
        PDCA-Planで必要な全データをまとめて返す
        """
        return {
            "act_logs": self.collect_act_logs(),
            "eval_results": self.collect_eval_results(),
            "market": self.collect_market_data(),
            # "tags": ... # 必要なら追加
        }

# スクリプト直接実行時のテスト用
if __name__ == "__main__":
    collector = PlanDataCollector()
    summary = collector.collect_all()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
