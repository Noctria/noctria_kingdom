# scripts/show_last_inventor_decision.py
from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import sys
from typing import Any, Dict, Optional


def parse_returned_value_from_log(text: str) -> Dict[str, Any]:
    """
    Airflowログの「Returned value was: ...」行を抽出して dict を返す。
    - JSON 文字列・Python dict 文字列の両方を許容
    - 最後に出現したものを優先
    """
    # 1行に収まっている想定
    matches = re.findall(r"Returned value was:\s+(.*)", text)
    if not matches:
        raise ValueError("no 'Returned value was:' line found in log")

    raw = matches[-1].strip()
    # まず JSON として
    try:
        return json.loads(raw)
    except Exception:
        # ダメなら Python リテラル
        try:
            return ast.literal_eval(raw)
        except Exception as e:
            raise ValueError(f"cannot parse Returned value body: {raw[:200]}...") from e


def find_log_file(
    log_root: str,
    dag_id: str,
    task_id: str,
    run_id: Optional[str] = None,
) -> str:
    """
    inventor_pipeline の taskログパスを見つける。
    例: /opt/airflow/logs/dag_id=inventor_pipeline/run_id=manual_xxx/task_id=run_inventor_and_decide/attempt=1.log
    """
    dag_glob = os.path.join(
        log_root, f"dag_id={dag_id}", f"run_id={run_id or '*'}", f"task_id={task_id}", "*"
    )
    candidates = sorted(glob.glob(dag_glob))
    if not candidates:
        raise FileNotFoundError(f"no log files under: {dag_glob}")
    return candidates[-1]  # 最新（辞書順=run_id/attemptで十分実用）


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show last inventor decision JSON from Airflow logs."
    )
    parser.add_argument("--dag-id", default="inventor_pipeline")
    parser.add_argument("--task-id", default="run_inventor_and_decide")
    parser.add_argument(
        "--log-root",
        default="/opt/airflow/logs",
        help="Airflow logs root (inside container).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Specific run_id (e.g. manual_1757...). If omitted, latest is used.",
    )
    parser.add_argument(
        "--save",
        default=None,
        help="Path to save the extracted JSON (inside container).",
    )
    parser.add_argument(
        "--assert-size",
        action="store_true",
        help="Exit with non-zero code if decision.size <= 0.",
    )
    args = parser.parse_args()

    try:
        log_path = find_log_file(args.log_root, args.dag_id, args.task_id, args.run_id)
        print(f":: file => {log_path}", file=sys.stderr)

        with open(log_path, encoding="utf-8") as f:
            text = f.read()

        data = parse_returned_value_from_log(text)

        # 整形して表示
        print(json.dumps(data, ensure_ascii=False, indent=2))

        # 保存オプション
        if args.save:
            os.makedirs(os.path.dirname(os.path.abspath(args.save)), exist_ok=True)
            with open(args.save, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f":: saved => {args.save}", file=sys.stderr)

        # 便利出力
        trace_id = data.get("trace_id")
        if trace_id:
            print(f":: trace_id => {trace_id}", file=sys.stderr)

        # アサート（CI用途）
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
