# /opt/airflow/scripts/show_last_inventor_decision.py
from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import sys
from typing import Any, Dict, Optional, List, Tuple


def _parse_returned_value_lines(text: str) -> List[str]:
    # 1行想定だが、ログによって末尾に余計な空白が付くことがあるので strip
    return [m.strip() for m in re.findall(r"Returned value was:\s+(.*)", text)]


def parse_returned_value_from_log(text: str) -> Dict[str, Any]:
    """
    Airflowログの「Returned value was: ...」から**最後に出たもの**を辞書化。
    JSON でも Python dict でもOK。
    """
    matches = _parse_returned_value_lines(text)
    if not matches:
        raise ValueError("no 'Returned value was:' line found in log")
    raw = matches[-1]
    try:
        return json.loads(raw)             # JSON 形式
    except Exception:
        return ast.literal_eval(raw)       # Python dict 形式


def _glob_latest(paths_glob: str, latest_by: str) -> str:
    cands = glob.glob(paths_glob)
    if not cands:
        raise FileNotFoundError(f"no log files under: {paths_glob}")
    if latest_by == "mtime":
        return max(cands, key=os.path.getmtime)
    # 既存互換：辞書順（推奨はmtime）
    return sorted(cands)[-1]


def find_log_file(
    log_root: str,
    dag_id: str,
    task_id: str,
    run_id: Optional[str],
    latest_by: str = "mtime",  # "mtime" | "lex"
) -> str:
    """
    例: /opt/airflow/logs/dag_id=inventor_pipeline/run_id=manual_xxx/task_id=run_inventor_and_decide/attempt=1.log
    """
    pat = os.path.join(
        log_root, f"dag_id={dag_id}", f"run_id={run_id or '*'}", f"task_id={task_id}", "*"
    )
    return _glob_latest(pat, latest_by)


def main() -> int:
    ap = argparse.ArgumentParser(description="Show last inventor decision JSON from Airflow logs.")
    ap.add_argument("--dag-id", default="inventor_pipeline")
    ap.add_argument("--task-id", default="run_inventor_and_decide")
    ap.add_argument("--log-root", default="/opt/airflow/logs")
    ap.add_argument("--run-id", default=None, help="Specify a run_id (otherwise latest is used)")
    ap.add_argument("--latest-by", default="mtime", choices=["mtime", "lex"], help="How to choose the latest log")
    ap.add_argument("--save", default=None, help="Save JSON to this path (inside container)")
    ap.add_argument("--assert-size", action="store_true", help="Exit non-zero if decision.size <= 0")
    args = ap.parse_args()

    try:
        log_path = find_log_file(args.log_root, args.dag_id, args.task_id, args.run_id, args.latest_by)
        print(f":: file => {log_path}", file=sys.stderr)

        with open(log_path, encoding="utf-8") as f:
            text = f.read()

        data = parse_returned_value_from_log(text)

        # 整形表示（STDOUT）
        print(json.dumps(data, ensure_ascii=False, indent=2))

        # 追加情報は STDERR
        trace_id = data.get("trace_id")
        if trace_id:
            print(f":: trace_id => {trace_id}", file=sys.stderr)

        # 保存
        if args.save:
            os.makedirs(os.path.dirname(os.path.abspath(args.save)), exist_ok=True)
            with open(args.save, "w", encoding="utf-8") as w:
                json.dump(data, w, ensure_ascii=False, indent=2)
            print(f":: saved => {args.save}", file=sys.stderr)

        # アサート（CI向け）
        if args.assert_size:
            size = None
            try:
                size = float(((data.get("decision") or {}).get("size")))
            except Exception:
                pass
            if not (isinstance(size, (int, float)) and size > 0):
                print("ASSERTION FAILED: decision.size <= 0", file=sys.stderr)
                return 2

        return 0
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
