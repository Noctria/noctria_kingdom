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


def export_logs_to_csv(logs: List[Dict], output_path: Path):
    """📤 昇格ログをCSV出力する"""
    if not logs:
        print("⚠️ ログが存在しません、CSV出力をスキップしました。")
        return

    # フィールド名をユニークなキーで定義（全ログからスキャン）
    fieldnames = sorted({key for log in logs for key in log.keys() if not key.startswith("__")})

    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for log in logs:
                writer.writerow({k: log.get(k, "") for k in fieldnames})
        print(f"✅ CSV出力完了: {output_path}")
    except Exception as e:
        print(f"⚠️ CSV出力失敗: {e}")


def reset_push_flag(strategy_name: str) -> bool:
    """
    🔁 指定戦略の `pushed` フラグを False に変更（再Push許可）
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
                    print(f"✅ pushed フラグを false に変更: {file.name}")
                    return True
        except Exception as e:
            print(f"⚠️ フラグ変更失敗: {file.name} - {e}")
    return False


def mark_for_reevaluation(strategy_name: str) -> bool:
    """
    🔄 指定戦略を再評価対象として VERITAS_EVAL_LOG に戻す
    """
    for file in ACT_LOG_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("strategy") == strategy_name:
                    # 評価ログへ追記
                    eval_data = []
                    if VERITAS_EVAL_LOG.exists():
                        with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as ef:
                            try:
                                loaded = json.load(ef)
                                if isinstance(loaded, list):
                                    eval_data = loaded
                                else:
                                    eval_data = [loaded]
                            except json.JSONDecodeError:
                                pass
                    eval_data.append(data)
                    with open(VERITAS_EVAL_LOG, "w", encoding="utf-8") as ef:
                        json.dump(eval_data, ef, indent=2, ensure_ascii=False)

                    # ACTログ削除
                    file.unlink()
                    print(f"🔁 再評価へ戻しました: {strategy_name}")
                    return True
        except Exception as e:
            print(f"⚠️ 再評価処理失敗: {file.name} - {e}")
    return False
