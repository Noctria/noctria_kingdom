from __future__ import annotations
import json, os, subprocess
from typing import List, Dict, Any

def run_pytest(tests: List[str]) -> Dict[str, Any]:
    """
    軽量テストだけを実行。外部プラグインを抑止し、src を PYTHONPATH に通す。
    失敗を簡易パースして返す（詳細は raw_log に格納）。
    """
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONPATH"] = os.path.abspath("./src")

    cmd = ["pytest", "-q"] + tests
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    out = p.stdout + "\n" + p.stderr

    failures: List[Dict[str, Any]] = []
    # 超簡易パース： "E   AssertionError: ..." 行や "FAILED test_x.py::..." を拾う
    for line in out.splitlines():
        if line.startswith("FAILED ") or line.strip().startswith("E   "):
            failures.append({"message": line})

    return {
        "returncode": p.returncode,
        "failures": failures,
        "raw_log": out,
    }
