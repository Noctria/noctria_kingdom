# scripts/show_last_inventor_decision.py
from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional


def _parse_returned_value_lines(text: str) -> List[str]:
    # Airflow のログにある "Returned value was: ..." 行をすべて拾う
    return [m.strip() for m in re.findall(r"Returned value was:\s+(.*)", text)]


def parse_returned_value_from_log(text: str) -> Dict[str, Any]:
    matches = _parse_returned_value_lines(text)
    if not matches:
        raise ValueError("no 'Returned value was:' line found in log")
    raw = matches[-1]
    try:
        return json.loads(raw)
    except Exception:
        return ast.literal_eval(raw)


def _all_attempt_logs(log_root: str, dag_id: str, task_id: str) -> List[str]:
    # 例: /opt/airflow/logs/dag_id=inventor_pipeline/run_id=*/task_id=run_inventor_and_decide/*
    pat = os.path.join(
        log_root, f"dag_id={dag_id}", "run_id=*",
        f"task_id={task_id}", "*"
    )
    # 新しい順（mtime降順）で返す
    return sorted(glob.glob(pat), key=os.path.getmtime, reverse=True)


def pick_log_path(
    log_root: str,
    dag_id: str,
    task_id: str,
    run_id: Optional[str],
    latest_by: str = "mtime",
    only_passed: bool = False,
) -> str:
    """
    選択ロジック:
      - run_id 指定あり: その run の最新 attempt ログ
      - run_id 未指定:
         - only_passed=False: 全attemptのうち最新
         - only_passed=True : パースして skipped でないもののうち最新
    """
    if run_id:
        pat = os.path.join(log_root, f"dag_id={dag_id}", f"run_id={run_id}", f"task_id={task_id}", "*")
        cands = glob.glob(pat)
        if not cands:
            raise FileNotFoundError(f"no logs for run_id={run_id}")
        return max(cands, key=os.path.getmtime) if latest_by == "mtime" else sorted(cands)[-1]

    # run_id未指定 → すべてのattemptログから選ぶ
    for p in _all_attempt_logs(log_root, dag_id, task_id):
        if not only_passed:
            return p  # 一番新しいもの
        # only_passed: 中身を見て skip でないものを選ぶ
        try:
            data = parse_returned_value_from_log(open(p, encoding="utf-8").read())
            if not data.get("skipped"):
                return p
        except Exception:
            continue
    raise FileNotFoundError("no suitable logs found (only_passed requested but none found)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Show last inventor decision JSON from Airflow logs.")
    ap.add_argument("--dag-id", default="inventor_pipeline")
    ap.add_argument("--task-id", default="run_inventor_and_decide")
    ap.add_argument("--log-root", default="/opt/airflow/logs")
    ap.add_argument("--run-id", default=None, help="Specify a run_id (otherwise latest is used)")
    ap.add_argument("--latest-by", default="mtime", choices=["mtime", "lex"], help="How to choose the latest log")
    ap.add_argument("--only-passed", action="store_true", help="Pick the latest PASSED run (skip ones are ignored)")
    ap.add_argument("--save", default=None, help="Save JSON to this path (inside container)")
    ap.add_argument("--assert-size", action="store_true",
                    help="Exit non-zero if decision.size <= 0 (fails on skipped)")
    ap.add_argument("--assert-size-passed", action="store_true",
                    help="Assert size>0 only when the picked run is not skipped (skipped -> exit 0)")
    args = ap.parse_args()

    try:
        log_path = pick_log_path(
            log_root=args.log_root,
            dag_id=args.dag_id,
            task_id=args.task_id,
            run_id=args.run_id,
            latest_by=args.latest_by,
            only_passed=args.only_passed,
        )
        print(f":: file => {log_path}", file=sys.stderr)

        text = open(log_path, encoding="utf-8").read()
        data = parse_returned_value_from_log(text)

        print(json.dumps(data, ensure_ascii=False, indent=2))
        if data.get("trace_id"):
            print(f":: trace_id => {data['trace_id']}", file=sys.stderr)

        if args.save:
            os.makedirs(os.path.dirname(os.path.abspath(args.save)), exist_ok=True)
            with open(args.save, "w", encoding="utf-8") as w:
                json.dump(data, w, ensure_ascii=False, indent=2)
            print(f":: saved => {args.save}", file=sys.stderr)

        # Assertions
        if args.assert_size:
            size = float(((data.get("decision") or {}).get("size", 0) or 0))
            if not (size > 0):
                print("ASSERTION FAILED: decision.size <= 0 (or skipped)", file=sys.stderr)
                return 2

        if args.assert_size_passed:
            if data.get("skipped"):
                # 最新が skip でも CI は成功扱いにする
                return 0
            size = float(((data.get("decision") or {}).get("size", 0) or 0))
            if not (size > 0):
                print("ASSERTION FAILED: decision.size <= 0", file=sys.stderr)
                return 2

        return 0
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
