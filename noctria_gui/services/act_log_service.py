#!/usr/bin/env python3
# coding: utf-8

"""
📜 Veritas昇格戦略ログサービス
- 昇格ログの読み込み、CSV出力、再処理支援
"""

import json
import csv
from typing import List, Dict
from pathlib import Path
from core.path_config import ACT_LOG_DIR, VERITAS_EVAL_LOG


def load_all_act_logs() -> List[Dict]:
    """📂 ACTログディレクトリから全ログを読み込む"""
    logs = []
    for file in sorted(ACT_LOG_DIR.glob("*.json"), reverse=True):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["__log_path__"] = str(file)
                logs.append(data)
        except Exception as e:
            print(f"⚠️ 読み込み失敗: {file.name} - {e}")
    return logs


def export_act_logs_to_csv(logs: List[Dict], output_path: Path):
    """📤 昇格ログをCSV出力する"""
    if not logs:
        return
    fieldnames = list(logs[0].keys())
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(logs)


def force_unpush_flag(strategy_name: str) -> bool:
    """
    🛠 指定戦略の `pushed: false` に強制変更（再Push可能にする）
    """
    for file in ACT_LOG_DIR.glob("*.json"):
        try:
            with open(file, "r+", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("strategy") == strategy_name:
                    data["pushed"] = False
                    f.seek(0)
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.truncate()
                    print(f"✅ pushed フラグを false に戻しました: {file.name}")
                    return True
        except Exception as e:
            print(f"⚠️ 書き込み失敗: {file.name} - {e}")
    return False


def move_to_evaluation(strategy_name: str) -> bool:
    """
    🔄 指定戦略を再評価に回す（評価結果JSONへ再投入）
    """
    for file in ACT_LOG_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("strategy") == strategy_name:
                    # 評価ログへ追記
                    if VERITAS_EVAL_LOG.exists():
                        with open(VERITAS_EVAL_LOG, "r+", encoding="utf-8") as ef:
                            try:
                                eval_data = json.load(ef)
                                if isinstance(eval_data, list):
                                    eval_data.append(data)
                                else:
                                    eval_data = [eval_data, data]
                            except:
                                eval_data = [data]
                            ef.seek(0)
                            json.dump(eval_data, ef, indent=2, ensure_ascii=False)
                            ef.truncate()
                    # 元のACTログは削除
                    file.unlink()
                    print(f"🔁 再評価キューへ戻しました: {strategy_name}")
                    return True
        except Exception as e:
            print(f"⚠️ 再評価処理失敗: {file.name} - {e}")
    return False
