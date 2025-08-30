# tests/conftest.py
from __future__ import annotations
import pytest

@pytest.fixture()
def capture_alerts(monkeypatch):
    """
    plan_data.observability.emit_alert の呼び出しを捕捉して検証できるようにする。
    返り値:
      alerts: list[dict] ・・・ emit_alert に渡された kwargs を記録
    """
    from plan_data import observability

    recorded: list[dict] = []

    def _fake_emit_alert(**kwargs):
        # kwargs には kind, reason, severity, trace_id, details, conn_str 等が入る
        recorded.append(dict(kwargs))
        return 1  # ダミーの alert id

    monkeypatch.setattr(observability, "emit_alert", _fake_emit_alert)
    return recorded
