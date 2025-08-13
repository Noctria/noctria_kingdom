# ============================================
# File: tests/test_trace_decision_e2e.py
# ============================================
import os
import re
import subprocess
import time

import pytest

@pytest.mark.integration
def test_decision_minidemo_writes_db(monkeypatch):
    """
    DSN は NOCTRIA_OBS_PG_DSN から取得。
    - obs_plan_runs / obs_infer_calls / obs_decisions / obs_exec_events に trace が書かれることを簡易確認
    """
    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    assert dsn is not None, "NOCTRIA_OBS_PG_DSN must be set for integration test."

    # 実行
    out = subprocess.check_output(
        ["python", "-m", "src.e2e.decision_minidemo"], text=True
    )
    m = re.search(r"trace_id=([A-Za-z0-9\-]+)", out)
    assert m, f"trace_id not found in output: {out}"
    trace_id = m.group(1)

    # psql でカウント（psql 前提。必要に応じて変更可能）
    def count(table: str) -> int:
        q = f"SELECT count(*) FROM {table} WHERE trace_id = '{trace_id}';"
        cmd = ["psql", dsn, "-t", "-c", q]
        c = subprocess.check_output(cmd, text=True).strip()
        return int(c)

    # 少し待機（コミットは autocommit だがCIの遅延吸収）
    time.sleep(0.5)

    assert count("obs_plan_runs") >= 2  # START/END
    assert count("obs_infer_calls") >= 1
    assert count("obs_decisions") >= 1
    assert count("obs_exec_events") >= 1
