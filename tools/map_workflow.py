#!/usr/bin/env python3
# coding: utf-8
"""
Noctria リポのワークフロー可視化ツール
- リポ直下から .py を走査して工程に自動分類
- import から工程間の依存を推定
- 可視化/レジストリ/CSV/JSON を artifacts/ に出力
"""

from __future__ import annotations

import ast
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "artifacts"
OUT_DIR.mkdir(exist_ok=True)

# ===== 工程定義（順序は上流→下流）==============================================
# キーワードはパス名/ファイル名/内容の単純一致 or 正規表現
STAGES: List[Tuple[str, List[str]]] = [
    (
        "01_info_collect",
        [
            r"\b(data|datasets|fetch|loader|ingest|scrape|collector)\b",
            r"\bsentiment|fundamental|tradingview|fred|market(_|)data\b",
            r"src/data|data/preprocessing|data/fundamental",
        ],
    ),
    (
        "02_analyze_raw",
        [
            r"\b(preprocess|clean|feature|integrat|explor|eda)\b",
            r"\bquality_gate|missing_ratio|data_lag\b",
        ],
    ),
    (
        "03_plan_build",
        [
            r"\b(plan|prompt|strategy_(generator|template)|hermes|veritas|cognitor)\b",
            r"prompts|veritas/generate|strateg(y|ies)",
        ],
    ),
    (
        "04_backtest",
        [
            r"\b(backtest|simulate|evaluation|evaluate|strategy_evaluator)\b",
            r"noctria_backtest_dag|simulate_strategy_dag",
        ],
    ),
    (
        "05_forward_test",
        [
            r"\b(forward|paper(?:trade)?|live(?:_dry)?|monitor)\b",
            r"trade_monitor|switch_to_best_model",
        ],
    ),
    (
        "06_fintokei_rule_check",
        [
            r"\bfintokei|risk_guard|policy_guard|governance|alignment\b",
            r"policy_guard|harmonia|quality_gate.*ALERT",
        ],
    ),
    (
        "07_order_mt5",
        [
            r"\b(order|execution|mt5|metatrader)\b",
            r"order_api|generate_order_json|execution",
        ],
    ),
    (
        "08_settlement",
        [
            r"\b(settle|closing|pnl|accounting|position_close)\b",
        ],
    ),
    (
        "09_result_analysis",
        [
            r"\b(report|analyz|analysis|explain|shap|lime|dashboard|pdca_log)\b",
            r"explainable_ai|processed_data_handler|pdca_log_parser",
        ],
    ),
    (
        "10_merge_new_info",
        [
            r"\b(merge|registry|decision|adopt|select|recheck|refactor)\b",
            r"pdca|decision|recheck",
        ],
    ),
    (
        "11_replan",
        [
            r"\b(apply_best_params|optimiz|optuna|plan)\b",
            r"optimize_params|apply_best_params",
        ],
    ),
]

# 除外パス（生成物や墓場など）
IGNORE_DIRS = {
    ".git",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "__pycache__",
    "actions-runner",
    "_graveyard",
    "generated_code",
    "data/models",
    ".ipynb_checkpoints",
}

PY_SUFFIX = ".py"


@dataclass
class FileEntry:
    path: str
    stage: Optional[str]
    reasons: List[str]
    imports: List[str]


# ===== ヘルパ ===============================================================


def iter_py_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix != PY_SUFFIX:
            continue
        parts = set(part for part in p.parts)
        if parts & IGNORE_DIRS:
            continue
        files.append(p)
    return files


def matches_any(patterns: List[str], text: str) -> Optional[str]:
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            return pat
    return None


def guess_stage(p: Path, content: str) -> Tuple[Optional[str], List[str]]:
    path_text = str(p).replace("\\", "/")
    fname = p.name
    hits: List[str] = []
    for stage, pats in STAGES:
        reason = (
            matches_any(pats, path_text)
            or matches_any(pats, fname)
            or matches_any(pats, content[:2000])
        )
        if reason:
            hits.append(f"{stage}:{reason}")
            return stage, hits
    return None, hits


def parse_imports(content: str) -> List[str]:
    out: List[str] = []
    try:
        t = ast.parse(content)
    except Exception:
        return out
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            for a in n.names:
                out.append(a.name)
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                out.append(n.module)
    return out


def module_to_stage(module: str) -> Optional[str]:
    # “import src.xxx.yyy” → パス風に見立ててステージ推定
    fake_path = module.replace(".", "/")
    for stage, pats in STAGES:
        if matches_any(pats, fake_path):
            return stage
    return None


# ===== メイン処理 ===========================================================


def main() -> None:
    files = iter_py_files(REPO_ROOT)
    entries: List[FileEntry] = []
    stage_to_files: Dict[str, List[str]] = defaultdict(list)

    for f in files:
        try:
            s = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            s = ""
        stage, reasons = guess_stage(f, s)
        imps = parse_imports(s)
        rel = str(f.relative_to(REPO_ROOT)).replace("\\", "/")
        entries.append(FileEntry(path=rel, stage=stage, reasons=reasons, imports=imps))
        if stage:
            stage_to_files[stage].append(rel)

    # 工程間エッジ（import から推定：ファイルの stage -> import先の stage）
    edges: Dict[Tuple[str, str], int] = defaultdict(int)
    for e in entries:
        if not e.stage:
            continue
        for m in e.imports:
            dst = module_to_stage(m)
            if dst and dst != e.stage:
                edges[(e.stage, dst)] += 1

    # 出力 1) JSON
    json_path = OUT_DIR / "workflow_map.json"
    json_path.write_text(
        json.dumps(
            {
                "entries": [asdict(e) for e in entries],
                "edges": [{"src": s, "dst": d, "count": c} for (s, d), c in edges.items()],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 出力 2) CSV
    csv_path = OUT_DIR / "workflow_map.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as w:
        writer = csv.writer(w)
        writer.writerow(["path", "stage", "reasons", "imports"])
        for e in entries:
            writer.writerow([e.path, e.stage or "", " | ".join(e.reasons), " ".join(e.imports)])

    # 出力 3) YAML（レジストリ固定化）
    yaml_path = OUT_DIR / "workflow_registry.yaml"

    def _yaml_escape(s: str) -> str:
        return s.replace('"', '\\"')

    lines = ["stages:"]
    for stage, _ in STAGES:
        lines.append(f'  - name: "{stage}"')
        files_list = stage_to_files.get(stage, [])
        lines.append("    files:")
        for fp in sorted(files_list):
            lines.append(f'      - "{_yaml_escape(fp)}"')
    yaml_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 出力 4) Mermaid（工程フロー）
    mmd_path = OUT_DIR / "workflow_graph.mmd"
    # ステージノード定義（件数入り）
    counts = {stage: len(stage_to_files.get(stage, [])) for stage, _ in STAGES}
    m_lines = ["flowchart LR"]
    for stage, _ in STAGES:
        m_lines.append(f'  {stage}["{stage}\\n({counts.get(stage,0)} files)"]')
    # エッジ（頻度付き）
    for (s, d), c in edges.items():
        m_lines.append(f"  {s} -->|{c}| {d}")
    mmd_path.write_text("\n".join(m_lines) + "\n", encoding="utf-8")

    # 出力 5) Graphviz DOT（お好みで）
    dot_path = OUT_DIR / "workflow_graph.dot"
    d_lines = ["digraph G {", "  rankdir=LR;"]
    for stage, _ in STAGES:
        d_lines.append(f'  "{stage}" [shape=box,label="{stage}\\n({counts.get(stage,0)} files)"];')
    for (s, d), c in edges.items():
        d_lines.append(f'  "{s}" -> "{d}" [label="{c}"];')
    d_lines.append("}")
    dot_path.write_text("\n".join(d_lines) + "\n", encoding="utf-8")

    # 要約
    summary = OUT_DIR / "workflow_map.README.md"
    summary.write_text(
        "# Noctria Workflow Map\n\n"
        "- Source: repo scan\n"
        f"- Files scanned: {len(files)}\n"
        f"- Stages covered: {sum(1 for _, _ in STAGES if counts.get(_,0) >= 0)}\n\n"
        "## Artifacts\n"
        "- `workflow_registry.yaml` — 固定化レジストリ（工程→担当ファイル）\n"
        "- `workflow_map.json` / `workflow_map.csv` — 生データ\n"
        "- `workflow_graph.mmd` — Mermaid フロー。GitHub/VSCode拡張で可視化\n"
        "- `workflow_graph.dot` — Graphviz\n",
        encoding="utf-8",
    )

    print("✅ Generated:")
    for p in [json_path, csv_path, yaml_path, mmd_path, dot_path, summary]:
        print(" -", p.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
