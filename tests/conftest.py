# tests/conftest.py
from __future__ import annotations
import os, sys, pytest

# --- ensure project src/ on sys.path ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
for p in (SRC, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

@pytest.fixture()
def capture_alerts(monkeypatch):
    """
    - PLAN: observability.emit_alert をキャプチャ
    - AIログ: observability.log_infer_call をダミー化（DB不要にする）
    """
    from plan_data import observability

    recorded: list[dict] = []

    def _fake_emit_alert(**kwargs):
        recorded.append(dict(kwargs))
        return 1  # dummy id

    def _fake_log_infer_call(*args, **kwargs):
        # propose_with_logging() から呼ばれるが、DB不要化のため no-op
        return 1

    monkeypatch.setattr(observability, "emit_alert", _fake_emit_alert)
    monkeypatch.setattr(observability, "log_infer_call", _fake_log_infer_call)
    return recorded
