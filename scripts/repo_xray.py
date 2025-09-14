#!/usr/bin/env python3
# scripts/repo_xray.py
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]

WF_DIRS = [ROOT / ".github" / "workflows"]
AIRFLOW_DIRS = [ROOT / "airflow_docker", ROOT / "dags", ROOT / "airflow_docker" / "dags"]
CODE_DIRS = [ROOT / "src", ROOT / "experts", ROOT / "autogen_scripts", ROOT / "tools", ROOT / "scripts"]

PATTERNS = {
    "inventor":  re.compile(r"\bInventor\b|inventor", re.I),
    "harmonia":  re.compile(r"\bHarmonia\b|harmonia|rerank", re.I),
    "pdca":      re.compile(r"\bPDCA\b|pdca_agent|decision", re.I),
    "veritas":   re.compile(r"\bVeritas\b|veritas|strategy", re.I),
    "airflow":   re.compile(r"\bairflow\b|DAG\s*\(", re.I),
}

# --- helpers ---
def read_text_safe(p: Path, limit_bytes: int = 200_000) -> str:
    try:
        b = p.read_bytes()
        if len(b) > limit_bytes:
            b = b[:limit_bytes]
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def list_files(dirs: List[Path], exts: Tuple[str,...] = (".py", ".yml", ".yaml", ".md")) -> List[Path]:
    out: List[Path] = []
    for d in dirs:
        if not d.exists(): 
            continue
        for p in d.rglob("*"):
            if p.is_file() and (p.suffix in exts or (p.suffix == "" and p.name.endswith(".yml"))):
                # skip large irrelevant dirs quickly
                if any(part in {"logs","data",".venv","node_modules"} for part in p.parts):
                    continue
                out.append(p)
    return out

def parse_workflow_meta(yml_text: str) -> Dict[str, str]:
    # very light regex parse (no PyYAML)
    name = ""
    on_line = ""
    for line in yml_text.splitlines():
        if not name:
            m = re.match(r"^\s*name:\s*(.+?)\s*$", line)
            if m: name = m.group(1).strip()
        if re.match(r"^\s*on:\s*", line):
            on_line = "on:"
        if name and on_line:
            break
    return {"name": name or "(no name)", "trigger": on_line or "(see file)"}

def parse_airflow_dag_ids(py_text: str) -> List[str]:
    ids = set()
    # dag_id="xxx"
    for m in re.finditer(r"dag_id\s*=\s*['\"]([^'\"]+)['\"]", py_text):
        ids.add(m.group(1))
    # with DAG("xxx", ...) OR with DAG(dag_id="xxx", ...)
    for m in re.finditer(r"with\s+DAG\s*\(\s*(['\"])([^'\"]+)\1", py_text):
        ids.add(m.group(2))
    return sorted(ids)

def grep_patterns(py_text: str) -> List[str]:
    hits = []
    for key, rx in PATTERNS.items():
        if rx.search(py_text):
            hits.append(key)
    return hits

def top_dirs() -> List[Tuple[int,str]]:
    # count files per dir (tracked by git)
    try:
        import subprocess
        res = subprocess.run(
            ["git","ls-files"], cwd=str(ROOT), check=True, capture_output=True, text=True
        )
        counts: Dict[str,int] = {}
        for line in res.stdout.splitlines():
            if "/" in line:
                d = line.rsplit("/",1)[0]
            else:
                d = "."
            counts[d] = counts.get(d,0)+1
        ranked = sorted(((c,d) for d,c in counts.items()), reverse=True)
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

    # Workflows
    wf_files = list_files(WF_DIRS, exts=(".yml",".yaml"))
    workflows = []
    for p in wf_files:
        t = read_text_safe(p)
        meta = parse_workflow_meta(t)
        workflows.append({
            "path": str(p.relative_to(root)),
            "name": meta["name"],
            "trigger_hint": meta["trigger"],
        })

    # Airflow DAGs
    dag_py = list_files(AIRFLOW_DIRS, exts=(".py",))
    dags = []
    for p in dag_py:
        t = read_text_safe(p)
        ids = parse_airflow_dag_ids(t)
        if ids:
            dags.append({
                "path": str(p.relative_to(root)),
                "dag_ids": ids
            })

    # Code hits by pattern
    code_files = list_files(CODE_DIRS, exts=(".py",".md",".yml",".yaml"))
    buckets: Dict[str, List[str]] = {k: [] for k in PATTERNS.keys()}
    for p in code_files:
        t = read_text_safe(p)
        hits = grep_patterns(t)
        for h in hits:
            buckets[h].append(str(p.relative_to(root)))

    # Top dirs
    dir_ranking = [{"count": c, "dir": d} for c,d in top_dirs()]

    result = {
        "root": str(root),
        "workflows": sorted(workflows, key=lambda x: x["path"]),
        "airflow_dags": sorted(dags, key=lambda x: x["path"]),
        "pattern_hits": {k: sorted(set(v)) for k,v in buckets.items()},
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

    print(json.dumps({
        "ok": True,
        "json": str(json_path),
        "md": str(md_path),
        "workflows": len(result["workflows"]),
        "airflow_dags": len(result["airflow_dags"]),
    }, ensure_ascii=False))

if __name__ == "__main__":
    sys.exit(main())
