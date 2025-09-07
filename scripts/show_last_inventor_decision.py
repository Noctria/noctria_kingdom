#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
show_last_inventor_decision.py

Airflow の inventor_pipeline の実行ログから直近 Run の結果を取得して表示するユーティリティ。
CI 強化オプション:
  - --since-minutes N: 直近 N 分以内の Run だけを対象にする（古い成功を誤検知しない）
  - --only-passed: スキップではない成功 Run（decision あり）だけを対象
  - --assert-size-passed: 対象 Run の decision.size > 0 を必須にする（満たさなければ非ゼロ終了）
  - --emit-metrics: Prometheus 1行メトリクス出力（size, skipped）
  - --save PATH: 表示した JSON を PATH に保存

想定ログ:
  /opt/airflow/logs/dag_id=inventor_pipeline/run_id=*/task_id=run_inventor_and_decide/*

抽出対象の行:
  "Returned value was: <JSON もしくは Python dict repr>"

JSON優先、失敗したら ast.literal_eval で Python dict も受ける。
"""

from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple

LOG_GLOB = "/opt/airflow/logs/dag_id=inventor_pipeline/run_id=*/task_id=run_inventor_and_decide/*"
RETURNED_PATTERN = re.compile(r"Returned value was:\s+(.*)")

def _iso_to_dt(s: str) -> Optional[datetime]:
    try:
        # "....Z" にも対応
        s2 = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s2)
    except Exception:
        return None

def _file_mtime_dt(path: str) -> datetime:
    try:
        return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def _load_result_from_log(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        m = RETURNED_PATTERN.findall(text)
        if not m:
            return None
        raw = m[-1].strip()
        # JSON優先
        try:
            return json.loads(raw)
        except Exception:
            # Python dict repr も許容
            return ast.literal_eval(raw)
    except Exception:
        return None

def _extract_created_at(result: Dict[str, Any]) -> Optional[datetime]:
    # 新スキーマ: result["meta"]["created_at"]
    meta = result.get("meta") if isinstance(result, dict) else None
    if isinstance(meta, dict):
        ca = meta.get("created_at")
        if isinstance(ca, str):
            dt = _iso_to_dt(ca)
            if dt:
                return dt
    # 旧スキーマ: 無し → None
    return None

def _is_passed_result(result: Dict[str, Any]) -> bool:
    # スキップRun（quality_gate 未通過）は "skipped": True を持つ
    if result.get("skipped") is True:
        return False
    # decision.size > 0 が成功Runの最低条件
    dec = result.get("decision") or {}
    size = dec.get("size", 0.0) if isinstance(dec, dict) else 0.0
    try:
        return float(size) > 0.0
    except Exception:
        return False

def _format_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)

def _emit_metrics(result: Dict[str, Any]) -> None:
    """
    Prometheus 1行メトリクスを標準出力へ。
    - size: noctria_inventor_decision_size{symbol, timeframe} <value>
    - skipped: noctria_inventor_decision_skipped{reason="<kind>"} 0|1
    """
    ctx = result.get("context") or {}
    symbol = str(ctx.get("symbol", "UNKNOWN"))
    timeframe = str(ctx.get("timeframe", "UNKNOWN"))

    dec = result.get("decision") or {}
    try:
        size = float(dec.get("size", 0.0))
    except Exception:
        size = 0.0

    skipped = bool(result.get("skipped", False))
    reason = str(result.get("reason", "")) if skipped else ""

    # reason タグはざっくり分類（長くなりすぎないよう簡略）
    if "quality_gate not passed" in reason:
        reason_tag = "quality_gate"
    elif "quality_threshold_not_met" in reason:
        reason_tag = "quality_gate"
    elif skipped:
        reason_tag = "other"
    else:
        reason_tag = "ok"

    # size メトリクス
    print(f'noctria_inventor_decision_size{{symbol="{symbol}",timeframe="{timeframe}"}} {size}')
    # skipped メトリクス
    val = 1 if skipped else 0
    print(f'noctria_inventor_decision_skipped{{reason="{reason_tag}"}} {val}')

def _pick_latest(
    only_passed: bool,
    since_minutes: Optional[int],
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    ログファイル群から条件に合う「最新」を選ぶ。
    - only_passed=True の場合は _is_passed_result(result) が True のもののみ
    - since_minutes が指定されていれば、その時間内に「作成（meta.created_at or ファイル更新時刻）」されたもののみ
    戻り値: (log_path, result) / 見つからなければ (None, None)
    """
    paths = sorted(glob.glob(LOG_GLOB))
    if not paths:
        return None, None

    # 新しい順に見る（末尾が新しい想定のため逆順で走査）
    paths = list(reversed(paths))

    now = datetime.now(timezone.utc)
    cutoff: Optional[datetime] = None
    if since_minutes is not None and since_minutes > 0:
        cutoff = now - timedelta(minutes=since_minutes)

    for p in paths:
        result = _load_result_from_log(p)
        if not isinstance(result, dict):
            continue

        # 時間フィルタ
        created_at = _extract_created_at(result) or _file_mtime_dt(p)
        if cutoff and created_at < cutoff:
            # 期間外（古すぎる）
            continue

        # 通過/任意のフィルタ
        if only_passed and not _is_passed_result(result):
            continue

        return p, result

    return None, None

def main() -> int:
    ap = argparse.ArgumentParser(description="Show last Inventor decision (from Airflow logs)")
    ap.add_argument("--only-passed", action="store_true", help="通過Run（skippedでない & size>0）だけ対象にする")
    ap.add_argument("--assert-size-passed", action="store_true", help="対象Runで decision.size>0 を必須にする（満たなければ非ゼロ終了）")
    ap.add_argument("--since-minutes", type=int, default=None, help="直近 N 分の Run だけを対象にする（古い成功の誤検知防止）")
    ap.add_argument("--emit-metrics", action="store_true", help="Prometheus 1行メトリクスを出力する（size/skipped）")
    ap.add_argument("--save", type=str, default=None, help="表示した JSON をファイル保存するパス（コンテナ内パス）")
    args = ap.parse_args()

    log_path, result = _pick_latest(only_passed=args.only_passed, since_minutes=args.since_minutes)

    if not log_path or not isinstance(result, dict):
        msg = "no logs matched conditions"
        if args.assert_size_passed:
            print(f"ERROR: {msg}", file=sys.stderr)
            return 2
        print(msg)
        return 0

    print(f":: file => {log_path}")

    # 通常表示
    # 通過指定時は trace_id があれば出す（ない旧スキーマはスキップ）
    trace_id = result.get("trace_id")
    if trace_id:
        print(f":: trace_id => {trace_id}")

    # JSON本体
    print(_format_json(result))

    # 保存
    if args.save:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(args.save)), exist_ok=True)
            with open(args.save, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f":: saved => {args.save}")
        except Exception as e:
            print(f"WARN: save failed: {e}", file=sys.stderr)

    # メトリクス
    if args.emit_metrics:
        _emit_metrics(result)

    # アサート
    if args.assert_size_passed:
        if not _is_passed_result(result):
            print("ASSERTION FAILED: decision.size <= 0 or skipped==True", file=sys.stderr)
            return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
