#!/usr/bin/env python3
# coding: utf-8

"""
📜 Veritas昇格戦略ログサービス
- 昇格ログの読み込み、検索フィルタ、CSV出力、再処理支援、個別取得
"""

import json
import csv
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

from core.path_config import ACT_LOG_DIR, VERITAS_EVAL_LOG


def load_all_act_logs() -> List[Dict]:
    """📂 ACTログディレクトリから全ログを読み込み、score整形"""
    logs = []
    for file in sorted(ACT_LOG_DIR.glob("*.json"), reverse=True):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["__log_path__"] = str(file)
                data = _normalize_score(data)
                logs.append(data)
        except Exception as e:
            print(f"⚠️ 読み込み失敗: {file.name} - {e}")
    return logs


def _normalize_score(log: Dict) -> Dict:
    """📐 scoreがdict型ならmeanだけ取り出す"""
    score = log.get("score")
    if isinstance(score, dict) and "mean" in score:
        log["score"] = score["mean"]
    return log


def filter_act_logs(
    logs: List[Dict],
    strategy_name: Optional[str] = None,
    tag: Optional[str] = None,
    score_range: Optional[Tuple[float, float]] = None,
    date_range: Optional[Tuple[datetime, datetime]] = None,
    pushed: Optional[bool] = None
) -> List[Dict]:
    """🔍 昇格ログのフィルタ処理"""
    filtered = logs

    if strategy_name:
        filtered = [log for log in filtered if strategy_name.lower() in log.get("strategy", "").lower()]

    if tag:
        filtered = [log for log in filtered if tag in log.get("tag", "")]

    if score_range:
        min_score, max_score = score_range
        filtered = [
            log for log in filtered
            if isinstance(log.get("score"), (int, float)) and min_score <= log["score"] <= max_score
        ]

    if date_range:
        start, end = date_range
        filtered = [
            log for log in filtered
            if "promoted_at" in log and _within_date_range(log["promoted_at"], start, end)
        ]

    if pushed is not None:
        filtered = [log for log in filtered if log.get("pushed", False) == pushed]

    return filtered


def _within_date_range(date_str: str, start: datetime, end: datetime) -> bool:
    try:
        dt = datetime.fromisoformat(date_str)
        return start <= dt <= end
    except Exception:
        return False


def export_logs_to_csv(logs: List[Dict], output_path: Path) -> bool:
    """📤 昇格ログをCSV出力する（辞書・リストはJSON化）"""
    if not logs:
        print("⚠️ ログが存在しません、CSV出力をスキップしました。")
        return False

    fieldnames = sorted({key for log in logs for key in log.keys() if not key.startswith("__")})

    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for log in logs:
                # 値が dict や list の場合は文字列に変換して出力
                safe_row = {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                    for k, v in log.items()
                    if k in fieldnames
                }
                writer.writerow(safe_row)
        print(f"✅ CSV出力完了: {output_path}")
        return True
    except Exception as e:
        print(f"⚠️ CSV出力失敗: {e}")
        return False


def reset_push_flag(strategy_name: str) -> bool:
    """🔁 指定戦略の `pushed` フラグを False に変更（再Push許可）"""
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
    """🔄 指定戦略を再評価対象として VERITAS_EVAL_LOG に戻す"""
    for file in ACT_LOG_DIR.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("strategy") == strategy_name:
                    eval_data = []
                    if VERITAS_EVAL_LOG.exists():
                        with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as ef:
                            try:
                                loaded = json.load(ef)
                                eval_data = loaded if isinstance(loaded, list) else [loaded]
                            except json.JSONDecodeError:
                                pass
                    eval_data.append(data)
                    with open(VERITAS_EVAL_LOG, "w", encoding="utf-8") as ef:
                        json.dump(eval_data, ef, indent=2, ensure_ascii=False)
                    file.unlink()
                    print(f"🔁 再評価へ戻しました: {strategy_name}")
                    return True
        except Exception as e:
            print(f"⚠️ 再評価処理失敗: {file.name} - {e}")
    return False


def get_log_by_strategy(strategy_name: str) -> Optional[Dict]:
    """🔎 指定戦略のログを1件取得（戦略名が一致する最初のもの）"""
    logs = load_all_act_logs()
    for log in logs:
        if log.get("strategy") == strategy_name:
            return log
    return None
