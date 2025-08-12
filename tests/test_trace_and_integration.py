# tests/test_trace_and_integration.py
import os
import re
import json
from pathlib import Path

import pytest


def test_trace_id_format():
    from src.plan_data.trace import new_trace_id
    tid = new_trace_id(symbol="USDJPY", timeframe="1d")
    # 例: 20250813-123045-USDJPY-1d-a1b2c3d4
    assert re.match(r"^\d{8}-\d{6}-[A-Z0-9\-_]+-[A-Za-z0-9\-_]+-[0-9a-f]{8}$", tid)


@pytest.mark.integration
def test_minidemo_writes_db(monkeypatch, stub_collector, stub_strategies, tmp_data_dir):
    """
    統合テスト（DB必須）:
      - NOCTRIA_OBS_PG_DSN が設定されていない場合は skip
      - 実際に obs_plan_runs / obs_infer_calls の件数が増えることを確認
      - なおネットは切る（collectorはスタブ済み）ので高速
    """
    dsn = os.getenv("NOCTRIA_OBS_PG_DSN")
    if not dsn:
        pytest.skip("NOCTRIA_OBS_PG_DSN が未設定のため skip")

    try:
        import psycopg2
    except Exception:
        pytest.skip("psycopg2 が見つからないため skip")

    # 事前件数
    def _count(table: str) -> int:
        with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            (n,) = cur.fetchone()
            return int(n)

    before_plan = _count("obs_plan_runs")
    before_infer = _count("obs_infer_calls")

    # 実行（DB書き込みは本物、ネットはオフ）
    from src.plan_data.plan_to_all_minidemo import main
    main()

    after_plan = _count("obs_plan_runs")
    after_infer = _count("obs_infer_calls")

    # 少なくとも 1 件以上増えている（features/analyzer で plan が、AI 呼び出しで infer が増える）
    assert after_plan > before_plan, "obs_plan_runs の件数が増えていません"
    assert after_infer > before_infer, "obs_infer_calls の件数が増えていません"
