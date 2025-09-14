#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
show_last_inventor_decision.py

Airflow の inventor_pipeline 実行ログから直近 Run の結果を抽出して表示するユーティリティ。

主な機能:
  - --since-minutes N         : 直近 N 分以内の Run だけを対象（古い成功の誤検知を防止）
  - --only-passed             : スキップでない成功 Run（decision.size>0）だけを対象
  - --assert-size-passed      : 対象 Run の decision.size>0 を必須に（満たなければ非ゼロ終了）
  - --emit-metrics            : Prometheus 1行メトリクス（size / skipped）を標準出力へ
  - --save PATH               : 表示した JSON をファイル保存（コンテナ内パス）
  - --json                    : 機械可読な JSON を「のみ」標準出力（見つからなければ {} を出力し exit 0）

抽出対象のログ:
  /opt/airflow/logs/dag_id=inventor_pipeline/run_id=*/task_id=run_inventor_and_decide/*

抽出対象の行:
  "Returned value was: <JSON または Python dict repr>"

“最新”の判定は run_id の辞書順ではなく、
result.meta.created_at（なければファイル mtime）で行います。
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
from typing import Any, Dict, Optional, Tuple, List

# ログ探索パスと抽出パターン
LOG_GLOB = "/opt/airflow/logs/dag_id=inventor_pipeline/run_id=*/task_id=run_inventor_and_decide/*"
RETURNED_PATTERN = re.compile(r"Returned value was:\s+(.*)")

# ---------- 基本ユーティリティ ----------

def _iso_to_dt(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def _file_mtime_dt(path: str) -> datetime:
    try:
        return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def _load_result_from_log(path: str) -> Optional[Dict[str, Any]]:
    """ログ内の 'Returned value was:' 行の JSON もしくは Python dict をパースして返す。"""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        matches = RETURNED_PATTERN.findall(text)
        if not matches:
            return None
        raw = matches[-1].strip()
        try:
            return json.loads(raw)             # JSON 優先
        except Exception:
            return ast.literal_eval(raw)       # Python dict repr も許容
    except Exception:
        return None

def _extract_created_at(result: Dict[str, Any]) -> Optional[datetime]:
    """result.meta.created_at（ISO）を datetime(UTC) にして返す。なければ None。"""
    meta = result.get("meta")
    if isinstance(meta, dict):
        ca = meta.get("created_at")
        if isinstance(ca, str):
            return _iso_to_dt(ca)
    return None

def _is_passed_result(result: Dict[str, Any]) -> bool:
    """スキップではなく decision.size > 0 を満たす場合に True。"""
    if result.get("skipped") is True:
        return False
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

# ---------- メトリクス出力 ----------

def _emit_metrics(result: Dict[str, Any]) -> None:
    """
    Prometheus 1行メトリクス:
      - noctria_inventor_decision_size{symbol,timeframe} <size>
      - noctria_inventor_decision_skipped{reason="<kind>"} 0|1
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

    if "quality_gate not passed" in reason or "quality_threshold_not_met" in reason:
        reason_tag = "quality_gate"
    elif skipped:
        reason_tag = "other"
    else:
        reason_tag = "ok"

    print(f'noctria_inventor_decision_size{{symbol="{symbol}",timeframe="{timeframe}"}} {size}')
    print(f'noctria_inventor_decision_skipped{{reason="{reason_tag}"}} {1 if skipped else 0}')

# ---------- 最新 Run の選定（created_at / mtime ベース） ----------

def _pick_latest(
    only_passed: bool,
    since_minutes: Optional[int],
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    ログファイル群から条件に合う“最新”を返す。
    - 並べ替えは created_at（なければ mtime）降順
    - since_minutes 指定時はその期間内のみ対象
    - only_passed=True なら decision.size>0 かつ skipped!=True のみ対象
    """
    paths: List[str] = glob.glob(LOG_GLOB)
    if not paths:
        return None, None

    now = datetime.now(timezone.utc)
    cutoff: Optional[datetime] = None
    if since_minutes and since_minutes > 0:
        cutoff = now - timedelta(minutes=since_minutes)

    candidates: List[Tuple[datetime, str, Dict[str, Any]]] = []
    for p in paths:
        result = _load_result_from_log(p)
        if not isinstance(result, dict):
            continue

        ts = _extract_created_at(result) or _file_mtime_dt(p)
        if cutoff and ts < cutoff:
            continue
        if only_passed and not _is_passed_result(result):
            continue

        candidates.append((ts, p, result))

    if not candidates:
        return None, None

    candidates.sort(key=lambda t: t[0], reverse=True)
    _, best_path, best_result = candidates[0]
    return best_path, best_result

# ---------- CLI ----------

def main() -> int:
    ap = argparse.ArgumentParser(description="Show last Inventor decision (from Airflow logs)")
    ap.add_argument("--only-passed", action="store_true",
                    help="通過Run（skippedでない & decision.size>0）だけを対象にする")
    ap.add_argument("--assert-size-passed", action="store_true",
                    help="対象Runで decision.size>0 を必須にする（満たなければ非ゼロ終了）")
    ap.add_argument("--since-minutes", type=int, default=None,
                    help="直近 N 分の Run だけを対象にする（古い成功の誤検知を防止）")
    ap.add_argument("--emit-metrics", action="store_true",
                    help="Prometheus 1行メトリクスを出力する（size/skipped）")
    ap.add_argument("--save", type=str, default=None,
                    help="表示した JSON をファイル保存するパス（コンテナ内パス）")
    # 追加: 機械可読JSONのみ吐く
    ap.add_argument("--json", action="store_true",
                    help="機械可読JSONを標準出力（見つからなければ {} を出力し、常に exit 0）")
    args = ap.parse_args()

    log_path, result = _pick_latest(only_passed=args.only_passed, since_minutes=args.since_minutes)

    # --json 指定時は“純粋な JSON だけ”を出力し、常に exit 0
    if args.json:
        payload: Dict[str, Any] = result if isinstance(result, dict) else {}
        # フォールバック: ログが無い環境（CIランナー等）では、既知の成果物パスから読む
        if not payload:
            from pathlib import Path
            for p in [
                Path("codex_reports/inventor_last.json"),
                Path("codex_reports/latest_inventor_decision.json"),
                Path("reports/latest_inventor_decision.json"),
                Path("airflow_docker/codex_reports/inventor_last.json"),
            ]:
                if p.is_file():
                    try:
                        payload = json.loads(p.read_text(encoding="utf-8"))
                        break
                    except Exception as e:
                        print(f"::warning:: failed to read fallback decision file {p}: {e}", file=sys.stderr)

        # 保存オプションがあれば保存（エラーでも終了コードは 0 にする）
        if args.save:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(args.save)), exist_ok=True)
                with open(args.save, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception as e:
                # JSON モードでは失敗しても終了コード 0 を維持
                print(f"::warning:: save failed: {e}", file=sys.stderr)
        # 純粋な JSON を標準出力
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    # ここから下は従来表示（人間向け）モード
    if not log_path or not isinstance(result, dict):
        msg = "ERROR: no logs matched conditions"
        if args.assert_size_passed:
            print(msg, file=sys.stderr)
            return 2
        print(msg)
        return 0

    print(f":: file => {log_path}")
    trace_id = result.get("trace_id")
    if trace_id:
        print(f":: trace_id => {trace_id}")

    print(_format_json(result))

    if args.save:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(args.save)), exist_ok=True)
            with open(args.save, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f":: saved => {args.save}")
        except Exception as e:
            print(f"WARN: save failed: {e}", file=sys.stderr)

    if args.emit_metrics:
        _emit_metrics(result)

    if args.assert_size_passed and not _is_passed_result(result):
        print("ASSERTION FAILED: decision.size <= 0 or skipped==True", file=sys.stderr)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
# adopt auto pr test
# adopt auto pr test
