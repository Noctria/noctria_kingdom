# [NOCTRIA_CORE_REQUIRED]
from __future__ import annotations

from pathlib import Path

import yaml

from src.core.path_config import PROJECT_ROOT, ensure_import_path

ensure_import_path()

POLS = PROJECT_ROOT / "codex_policies"


def _load(p):
    return yaml.safe_load(Path(p).read_text(encoding="utf-8"))


def check_strategy_protocol(artifact_dir: Path) -> list[str]:
    proto = _load(POLS / "strategy_protocol.yaml")
    set(proto["design_spec"]["required_fields"])
    missing = []
    # 簡易: design.mdに章見出しがあるか、backtest_config.yamlがあるか等
    if not (artifact_dir / "design.md").exists():
        missing.append("design.md_missing")
    if not (artifact_dir / "backtest_config.yaml").exists():
        missing.append("backtest_config_missing")
    # feature_vector 添付チェック
    if not (artifact_dir / "feature_vector.json").exists():
        missing.append("feature_vector_missing")
    return missing


def check_eval_protocol(report_dir: Path) -> list[str]:
    proto = _load(POLS / "eval_protocol.yaml")
    missing = []
    # 必須アーティファクト
    for f in ["equity_curve.png", "drawdown.png", "trades.csv", "meta.json"]:
        if not (report_dir / f).exists():
            missing.append(f"{f}_missing")
    # 予測確率のログ
    meta = _load(report_dir / "meta.json") if (report_dir / "meta.json").exists() else {}
    if proto["logging"]["predicted_prob_required"] and not meta.get("predicted_prob_logged"):
        missing.append("predicted_prob_not_logged")
    return missing
