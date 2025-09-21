#!/usr/bin/env python3
# scripts/repo_xray.py
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]

# 走査対象ディレクトリ（重複防止のため親ディレクトリを外す）
WF_DIRS = [ROOT / ".github" / "workflows"]
AIRFLOW_DIRS = [ROOT / "airflow_docker" / "dags", ROOT / "dags"]
CODE_DIRS = [
    ROOT / "src",
    ROOT / "experts",
    ROOT / "autogen_scripts",
    ROOT / "tools",
    ROOT / "scripts",
]

PATTERNS = {
    "inventor": re.compile(r"\bInventor\b|inventor", re.I),
    "harmonia": re.compile(r"\bHarmonia\b|harmonia|rerank", re.I),
    "pdca": re.compile(r"\bPDCA\b|pdca_agent|decision", re.I),
    "veritas": re.compile(r"\bVeritas\b|veritas|strategy", re.I),
    "airflow": re.compile(r"\bairflow\b|DAG\s*\(", re.I),
}


def read_text_safe(p: Path, limit_bytes: int = 200_000) -> str:
    try:
        b = p.read_bytes()
        if len(b) > limit_bytes:
            b = b[:limit_bytes]
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def list_files(
    dirs: List[Path], exts: Tuple[str, ...] = (".py", ".yml", ".yaml", ".md")
) -> List[Path]:
    """重複パスを絶対パスで排除しつつ収集"""
    seen = set()
    out: List[Path] = []
    for d in dirs:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            if not (p.suffix in exts or p.name.endswith(".yml")):
                continue
            if any(part in {"logs", "data", ".venv", "node_modules"} for part in p.parts):
                continue
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            out.append(rp)
    return out


def parse_workflow_meta(yml_text: str) -> Dict[str, str]:
    # very light parse（PyYAML不使用）
    name = ""
    has_on = False
    for line in yml_text.splitlines():
        if not name:
            m = re.match(r"^\s*name:\s*(.+?)\s*$", line)
            if m:
                name = m.group(1).strip()
        if re.match(r"^\s*on\s*:", line):
            has_on = True
        if name and has_on:
            break
    return {"name": name or "(no name)", "valid": has_on}


def parse_airflow_dag_ids(py_text: str) -> List[str]:
    ids = set()
    for m in re.finditer(r"dag_id\s*=\s*['\"]([^'\"]+)['\"]", py_text):
        ids.add(m.group(1))
    for m in re.finditer(r"with\s+DAG\s*\(\s*(['\"])([^'\"]+)\1", py_text):
        ids.add(m.group(2))
    return sorted(ids)


def grep_patterns(txt: str) -> List[str]:
    hits = []
    for key, rx in PATTERNS.items():
        if rx.search(txt):
            hits.append(key)
    return hits


def git_top_dirs() -> List[Tuple[int, str]]:
    try:
        import subprocess

        res = subprocess.run(
            ["git", "ls-files"], cwd=str(ROOT), check=True, capture_output=True, text=True
        )
        counts: Dict[str, int] = {}
        for line in res.stdout.splitlines():
            d = line.rsplit("/", 1)[0] if "/" in line else "."
            counts[d] = counts.get(d, 0) + 1
        ranked = sorted(((c, d) for d, c in counts.items()), reverse=True)
        return ranked[:20]
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default="codex_reports/repo_xray")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_base = Path(args.out)
    out_base.parent.mkdir(parents=True, exist_ok=True)

    # Workflows（on: が無い yml は除外）
    wf_files = list_files(WF_DIRS, exts=(".yml", ".yaml"))
    workflows = []
    for p in wf_files:
        t = read_text_safe(p)
        meta = parse_workflow_meta(t)
        if not meta["valid"]:
            continue
        workflows.append(
            {"path": str(p.relative_to(root)), "name": meta["name"], "trigger_hint": "on:"}
        )

    # Airflow DAGs（重複排除済のファイル集合から抽出）
    dag_py = list_files(AIRFLOW_DIRS, exts=(".py",))
    dags = []
    for p in dag_py:
        t = read_text_safe(p)
        ids = parse_airflow_dag_ids(t)
        if ids:
            dags.append({"path": str(p.relative_to(root)), "dag_ids": ids})

    # Pattern hits
    code_files = list_files(CODE_DIRS, exts=(".py", ".md", ".yml", ".yaml"))
    buckets: Dict[str, List[str]] = {k: [] for k in PATTERNS.keys()}
    for p in code_files:
        t = read_text_safe(p)
        for h in grep_patterns(t):
            buckets[h].append(str(p.relative_to(root)))
    buckets = {k: sorted(set(v)) for k, v in buckets.items()}

    # Top dirs
    dir_ranking = [{"count": c, "dir": d} for c, d in git_top_dirs()]

    result = {
        "root": str(root),
        "workflows": sorted(workflows, key=lambda x: x["path"]),
        "airflow_dags": sorted(dags, key=lambda x: x["path"]),
        "pattern_hits": buckets,
        "dir_ranking": dir_ranking,
    }

    # JSON
    json_path = out_base.with_suffix(".json")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown
    md = []
    md.append(f"# Repo X-Ray\n\nRoot: `{root}`\n")
    md.append("## Workflows\n")
    if result["workflows"]:
        for w in result["workflows"]:
            md.append(f"- `{w['path']}` — **{w['name']}** ({w['trigger_hint']})")
    else:
        md.append("- (none)")
    md.append("\n## Airflow DAGs\n")
    if result["airflow_dags"]:
        for d in result["airflow_dags"]:
            md.append(f"- `{d['path']}` — dag_id: " + ", ".join(f"`{i}`" for i in d["dag_ids"]))
    else:
        md.append("- (none)")
    md.append("\n## Pattern Hits\n")
    for key, files in result["pattern_hits"].items():
        md.append(f"### {key}")
        if files:
            for f in files[:200]:
                md.append(f"- `{f}`")
            if len(files) > 200:
                md.append(f"- ...and {len(files)-200} more")
        else:
            md.append("- (none)")
        md.append("")
    md.append("## Top Directories (tracked by git)\n")
    for row in result["dir_ranking"]:
        md.append(f"- {row['count']:>4}  `{row['dir']}`")
    md_path = out_base.with_suffix(".md")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "json": str(json_path),
                "md": str(md_path),
                "workflows": len(result["workflows"]),
                "airflow_dags": len(result["airflow_dags"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
