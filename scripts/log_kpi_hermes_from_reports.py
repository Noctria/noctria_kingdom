#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path
from src.core.path_config import ensure_import_path, PROJECT_ROOT
ensure_import_path()
from src.codex.obs_kpi import log_kpi

REQUIRED = [r'^#\s*Why it works', r'^#\s*Failure modes', r'^#\s*Counterfactual']
REPORTS = PROJECT_ROOT/"reports"

def main():
    if not REPORTS.exists():
        print("[kpi] no reports dir; skip", file=sys.stderr); return 0
    dirs = [p for p in REPORTS.iterdir() if p.is_dir()]
    if not dirs:
        print("[kpi] no report; skip", file=sys.stderr); return 0
    rep = sorted(dirs)[-1]
    md = rep/"explanation.md"
    if not md.exists():
        print("[kpi] no explanation.md; skip", file=sys.stderr); return 0
    text = md.read_text(encoding="utf-8")
    hits = sum(1 for pat in REQUIRED if re.search(pat, text, flags=re.M))
    coverage = hits/len(REQUIRED)
    # ここでは counterfactual_quality_score は簡易に coverage と同値でログ
    log_kpi("Hermes","explanation_coverage", coverage, {"report":rep.name})
    log_kpi("Hermes","counterfactual_quality_score", coverage, {"report":rep.name})
    print(f"[kpi] explanation_coverage={coverage:.2f} ({rep.name})")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
