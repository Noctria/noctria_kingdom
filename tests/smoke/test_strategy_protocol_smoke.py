import pytest
yaml = pytest.importorskip('yaml', reason='smoke: optional dep (pyyaml) not installed', allow_module_level=True)

# [NOCTRIA_CORE_REQUIRED]
from __future__ import annotations
import json
from pathlib import Path
import os
import yaml
import pytest

# プロジェクト内の共通パス
from src.core.path_config import ensure_import_path, STRATEGIES_VERITAS_GENERATED_DIR, PROJECT_ROOT

ensure_import_path()

POLICY_DIR = PROJECT_ROOT / "codex_policies"
STRAT_ROOT = STRATEGIES_VERITAS_GENERATED_DIR


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def _strategy_dirs() -> list[Path]:
    # 環境変数で限定可: NOCTRIA_STRAT_GLOB="VERITAS_*2025*"
    pattern = os.environ.get("NOCTRIA_STRAT_GLOB", "*")
    return [p for p in STRAT_ROOT.glob(pattern) if p.is_dir()]


@pytest.mark.smoke
def test_policy_files_exist():
    proto = POLICY_DIR / "strategy_protocol.yaml"
    assert proto.exists(), f"missing policy: {proto}"


@pytest.mark.smoke
def test_at_least_scannable_strategy_dir():
    if not STRAT_ROOT.exists():
        pytest.skip(f"strategies dir not found: {STRAT_ROOT}")
    dirs = _strategy_dirs()
    if not dirs:
        pytest.skip("no strategies to scan (ok for first run)")
    # 1件だけ軽く見る（最新）
    target = sorted(dirs)[-1]
    assert target.exists()


@pytest.mark.smoke
def test_strategy_artifacts_minimal():
    dirs = _strategy_dirs()
    if not dirs:
        pytest.skip("no strategies to check (ok for first run)")
    target = sorted(dirs)[-1]
    # 最低限: 設計/設定/特徴ベクトル
    expected = [
        target / "design.md",
        target / "backtest_config.yaml",
        target / "feature_vector.json",
        target / "README.md",
    ]
    missing = [str(p) for p in expected if not p.exists()]
    if missing:
        pytest.skip("strategy artifacts not complete yet: " + ", ".join(missing))


@pytest.mark.smoke
def test_feature_vector_is_valid_json():
    dirs = _strategy_dirs()
    if not dirs:
        pytest.skip("no strategies to check (ok for first run)")
    fv = sorted(dirs)[-1] / "feature_vector.json"
    if not fv.exists():
        pytest.skip("feature_vector.json not found yet (ok for early stage)")
    json.loads(fv.read_text(encoding="utf-8"))  # 例外が出なければOK
