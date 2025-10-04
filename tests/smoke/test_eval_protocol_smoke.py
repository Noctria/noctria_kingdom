# [NOCTRIA_CORE_REQUIRED]
from __future__ import annotations
import pytest
yaml = pytest.importorskip('yaml', reason='smoke: optional dep (pyyaml) not installed')

from pathlib import Path
import json
import yaml
import pytest

from src.core.path_config import ensure_import_path, PROJECT_ROOT

ensure_import_path()

POLICY_DIR = PROJECT_ROOT / "codex_policies"
REPORTS_DIR = PROJECT_ROOT / "reports"


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def _latest_report_dir() -> Path | None:
    if not REPORTS_DIR.exists():
        return None
    # 例: reports/VERITAS_FOO_20250926/
    cands = [p for p in REPORTS_DIR.iterdir() if p.is_dir()]
    return sorted(cands)[-1] if cands else None


@pytest.mark.smoke
def test_eval_policy_exists():
    proto = POLICY_DIR / "eval_protocol.yaml"
    assert proto.exists(), f"missing policy: {proto}"


@pytest.mark.smoke
def test_reports_dir_or_skip():
    if not REPORTS_DIR.exists():
        pytest.skip(f"reports dir not found: {REPORTS_DIR}")
    latest = _latest_report_dir()
    if latest is None:
        pytest.skip("no evaluation report yet (ok for first run)")
    assert latest.exists()


@pytest.mark.smoke
def test_eval_min_artifacts_or_skip():
    latest = _latest_report_dir()
    if latest is None:
        pytest.skip("no evaluation report yet")
    required = [
        latest / "equity_curve.png",
        latest / "drawdown.png",
        latest / "trades.csv",
        latest / "meta.json",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        pytest.skip("eval artifacts not complete yet: " + ", ".join(missing))


@pytest.mark.smoke
def test_predicted_prob_logged_or_skip():
    latest = _latest_report_dir()
    if latest is None:
        pytest.skip("no evaluation report yet")
    meta = latest / "meta.json"
    if not meta.exists():
        pytest.skip("meta.json not found yet")
    m = json.loads(meta.read_text(encoding="utf-8"))
    if not m.get("predicted_prob_logged", False):
        pytest.skip("predicted_prob not logged yet (guardrails will enforce later)")
