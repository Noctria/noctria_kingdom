# scripts/noctria_dead_code_detector.py
# -*- coding: utf-8 -*-
"""
Noctria Dead Code Detector — 不要化候補の自動抽出（CSV/MD/隔離コマンド）
- 根拠:
  * import 依存（Canonから到達不能 / 被参照0）
  * FastAPI/Airflow/Template参照シグナル（役割の有無）
  * Git最終コミット日（stale）
  * tests/ からの参照有無
  * coverage.xml（任意）で実行カバレッジ0判定
  * ルート→テンプレ参照（未参照テンプレ検出）
- 出力:
  * codex_reports/dead_code/report.csv
  * codex_reports/dead_code/report.md
  * codex_reports/dead_code/quarantine.sh（git mvコマンドの提案）
使い方:
  python3 scripts/noctria_dead_code_detector.py \
    [--canon docs/architecture/canon.yaml] \
    [--coverage coverage.xml] \
    [--obs-json codex_reports/runtime_calls.json] \
    [--stale-days 180] \
    [--graveyard _graveyard/$(date +%F)]
"""
from __future__ import annotations
import os, re, ast, csv, json, argparse, subprocess, time
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "codex_reports" / "dead_code"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCAN_DIRS = [
    ROOT / "src",
    ROOT / "noctria_gui" / "routes",
    ROOT / "noctria_gui" / "templates",
    ROOT / "airflow_docker" / "dags",
]

DEFAULT_CANON = [
    "noctria_gui/main.py",
    "noctria_gui/routes",
    "airflow_docker/dags",
    "src/plan_data",
    "src/core/decision_registry.py",
    "src/plan_data/observability.py",
]

# ---------- ユーティリティ ----------
def rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")

def walk_files() -> List[Path]:
    for base in SCAN_DIRS:
        if not base.exists(): continue
        for p in base.rglob("*"):
            if p.is_file():
                if any(seg in p.parts for seg in (".venv","venv_gui","venv_noctria","__pycache__","node_modules","dist","build","_graveyard")):
                    continue
                yield p

def is_py(p: Path) -> bool: return p.suffix == ".py"
def is_tpl(p: Path) -> bool: return p.suffix in (".html",".jinja",".j2")

def load_canon(path: Optional[Path]) -> List[str]:
    if not path or not path.exists(): return DEFAULT_CANON
    globs: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s: continue
        if s.startswith("- "): s = s[2:].strip()
        if s.startswith("#") or ":" in s: continue
        if re.match(r"^[\w./*-]+$", s): globs.append(s)
    return globs or DEFAULT_CANON

def git_days_since_last_commit(p: Path) -> Optional[int]:
    try:
        out = subprocess.check_output(["git","log","-1","--format=%ct", rel(p)], cwd=ROOT).decode().strip()
        if not out: return None
        t = int(out); return int((time.time()-t)//86400)
    except Exception:
        return None

# ---------- 解析（AST, 参照, シグナル） ----------
class PySignals(ast.NodeVisitor):
    def __init__(self, text: str):
        self.imports: Set[str] = set()
        self.fastapi = False
        self.airflow = False
        self.templates: Set[str] = set()
        self.text = text
    def visit_Import(self, n: ast.Import):  # type: ignore[override]
        for a in n.names: self.imports.add(a.name)
    def visit_ImportFrom(self, n: ast.ImportFrom):  # type: ignore[override]
        self.imports.add(n.module or "")
    def visit_Call(self, n: ast.Call):  # type: ignore[override]
        if isinstance(n.func, ast.Attribute) and n.func.attr in ("include_router","add_api_route"):
            self.fastapi = True
        if isinstance(n.func, ast.Name) and n.func.id == "DAG":
            self.airflow = True
        # TemplateResponse("file.html")
        def _tmpl_arg(node):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                return node.args[0].value
        if isinstance(n.func, ast.Name) and n.func.id == "TemplateResponse":
            v = _tmpl_arg(n); 
            if v: self.templates.add(v)
        if isinstance(n.func, ast.Attribute) and n.func.attr == "TemplateResponse":
            v = _tmpl_arg(n); 
            if v: self.templates.add(v)
        self.generic_visit(n)

def parse_py(p: Path) -> PySignals:
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(t)
    except Exception:
        t = ""; tree = ast.parse("pass")
    sig = PySignals(t); sig.visit(tree); return sig

def build_module_index(py_files: List[Path]) -> Dict[str, Path]:
    return { rel(p)[:-3].replace("/", "."): p for p in py_files }

def build_graph(py_files: List[Path], tpl_files: List[Path]):
    mod_idx = build_module_index(py_files)
    modules = set(mod_idx.keys())
    deps: Dict[str, Set[str]] = defaultdict(set)
    rdeps: Dict[str, int] = defaultdict(int)
    fastapi: Set[str] = set()
    airflow: Set[str] = set()
    tpl_index = { Path(rel(t)).name: rel(t) for t in tpl_files }

    for p in py_files:
        mod_from = rel(p)[:-3].replace("/", ".")
        sig = parse_py(p)
        for imp in sig.imports:
            target = None
            if imp in modules:
                target = imp
            else:
                cands = [m for m in modules if imp == m or imp.startswith(m+".")]
                if cands: target = max(cands, key=len)
            if target and target != mod_from:
                deps[mod_from].add(target)
                rdeps[target] += 1
        if sig.fastapi: fastapi.add(mod_from)
        if sig.airflow: airflow.add(mod_from)
        for name in sig.templates:
            if name in tpl_index:
                deps[mod_from].add(tpl_index[name])  # module->template (path)

    return mod_idx, deps, rdeps, fastapi, airflow

def reachable_from_canon(deps: Dict[str, Set[str]], canon_paths: List[str]) -> Set[str]:
    canon_mods: Set[str] = set()
    for c in canon_paths:
        cp = ROOT / c
        if cp.is_dir():
            for p in cp.rglob("*.py"):
                canon_mods.add(rel(p)[:-3].replace("/", "."))
        elif cp.is_file() and cp.suffix==".py":
            canon_mods.add(rel(cp)[:-3].replace("/", "."))
    seen: Set[str] = set()
    dq = deque(canon_mods)
    while dq:
        u = dq.popleft()
        if u in seen: continue
        seen.add(u)
        for v in deps.get(u, ()):
            if v not in seen and isinstance(v, str) and not v.endswith((".html",".jinja",".j2")):
                dq.append(v)
    return seen

# ---------- coverage / tests / obs ----------
def load_coverage_paths(xml_path: Optional[Path]) -> Set[str]:
    if not xml_path or not xml_path.exists(): return set()
    txt = xml_path.read_text(encoding="utf-8", errors="ignore")
    # <class name="..." filename="src/plan_data/statistics.py" ...
    paths = set(re.findall(r'filename="([^"]+)"', txt))
    return { p.replace("\\","/") for p in paths }

def tests_reference_name(target: Path) -> bool:
    tests_dir = ROOT / "tests"
    if not tests_dir.exists(): return False
    name = target.stem
    pat = re.compile(rf'\b{re.escape(name)}\b')
    for t in tests_dir.rglob("*.py"):
        try:
            if pat.search(t.read_text(encoding="utf-8", errors="ignore")):
                return True
        except Exception:
            pass
    return False

def load_obs_json(path: Optional[Path]) -> Set[str]:
    """
    任意: 形は [{"path":"src/plan_data/statistics.py", "ts":"..."}]
    など。path の集合だけ使う。
    """
    if not path or not path.exists(): return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        s = set()
        for row in data:
            p = str(row.get("path","")).replace("\\","/")
            if p: s.add(p)
        return s
    except Exception:
        return set()

# ---------- 判定 ----------
def classify_file(p: Path, mod_idx, deps, rdeps, reach, fastapi, airflow,
                  coverage_paths, obs_paths, stale_days_thresh: int):
    rp = rel(p)
    is_pyf = is_py(p); is_tplf = is_tpl(p)
    days = git_days_since_last_commit(p)

    categories: List[str] = []
    reasons: List[str] = []

    if is_pyf:
        mod = rp[:-3].replace("/", ".")
        indeg = rdeps.get(mod, 0)
        if mod not in reach:
            categories.append("orphaned")
            reasons.append("canon_unreachable")
        if indeg == 0:
            categories.append("unreferenced")
            reasons.append("in_degree=0")
        if (rp not in coverage_paths) and (not tests_reference_name(p)):
            categories.append("untested")
            reasons.append("no_coverage_no_tests")
        if days is not None and days > stale_days_thresh:
            categories.append("stale")
            reasons.append(f"last_commit>{stale_days_thresh}d")
        if mod in fastapi or mod in airflow:
            reasons.append("has_framework_signal")
    elif is_tplf:
        # どのルートからも参照されていないテンプレ
        used = False
        for a, outs in deps.items():
            if rp in outs:
                used = True; break
        if not used:
            categories.append("unused_template")
            reasons.append("no_route_reference")
        if days is not None and days > stale_days_thresh:
            categories.append("stale_tpl")
            reasons.append(f"last_commit>{stale_days_thresh}d")

    # 実行痕跡
    if rp in obs_paths:
        reasons.append("runtime_seen")

    return {
        "path": rp,
        "is_python": int(is_pyf),
        "is_template": int(is_tplf),
        "in_degree": (rdeps.get(rp[:-3].replace("/", "."), 0) if is_pyf else ""),
        "reachable_from_canon": int(is_pyf and (rp[:-3].replace("/", ".") in reach)),
        "fastapi_or_airflow_signal": int(is_pyf and ((rp[:-3].replace("/", ".") in fastapi) or (rp[:-3].replace("/", ".") in airflow))),
        "days_since_last_commit": days if days is not None else "",
        "has_coverage": int(rp in coverage_paths),
        "tests_ref": int(tests_reference_name(p)),
        "runtime_seen": int(rp in obs_paths),
        "categories": ",".join(sorted(set(categories))),
        "reasons": ",".join(sorted(set(reasons))),
    }

# ---------- メイン ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canon", default=None, help="canon.yaml path")
    ap.add_argument("--coverage", default=None, help="coverage.xml path (optional)")
    ap.add_argument("--obs-json", default=None, help="runtime call paths json (optional)")
    ap.add_argument("--stale-days", type=int, default=180)
    ap.add_argument("--graveyard", default="_graveyard/auto")
    args = ap.parse_args()

    canon = load_canon(Path(args.canon) if args.canon else None)
    files = list(walk_files())
    py_files = [p for p in files if is_py(p)]
    tpl_files = [p for p in files if is_tpl(p)]

    mod_idx, deps, rdeps, fastapi, airflow = build_graph(py_files, tpl_files)
    reach = reachable_from_canon(deps, canon)
    coverage_paths = load_coverage_paths(Path(args.coverage) if args.coverage else None)
    obs_paths = load_obs_json(Path(args.obs_json) if args.obs_json else None)

    rows = []
    for p in files:
        rows.append(classify_file(p, mod_idx, deps, rdeps, reach, fastapi, airflow,
                                  coverage_paths, obs_paths, args.stale_days))

    # CSV
    csv_path = OUT_DIR / "report.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # MD（要注目候補）
    dead = [r for r in rows if r["categories"] and any(c in r["categories"] for c in ("orphaned","unreferenced","unused_template"))]
    dead = sorted(dead, key=lambda r: (r["categories"], r["path"]))

    def mk_tbl(items):
        head = "|categories|path|days|in_deg|canon|cov|tests|runtime|reasons|\n|:--|:--|--:|--:|:--:|:--:|:--:|:--:|:--|\n"
        lines = []
        for r in items:
            lines.append(f'|{r["categories"]}|{r["path"]}|{r["days_since_last_commit"]}|{r["in_degree"] or ""}|{r["reachable_from_canon"]}|{r["has_coverage"]}|{r["tests_ref"]}|{r["runtime_seen"]}|{r["reasons"]}|')
        return head + "\n".join(lines)

    md_path = OUT_DIR / "report.md"
    md_path.write_text(
f"""# Dead Code Report (candidates)

- canon: `{args.canon or "<DEFAULT>"}`
- coverage: `{args.coverage or "<none>"}`
- runtime json: `{args.obs_json or "<none>"}`
- stale threshold: {args.stale_days} days

## ⚠️ Deletion/Quarantine candidates
{mk_tbl(dead)}

> 注: “orphaned”=Canonから到達不能 / “unreferenced”=被参照0 / “unused_template”=未参照テンプレ<br/>
> “runtime_seen”=実行痕跡あり → 即削除は避ける
""", encoding="utf-8")

    # 隔離提案シェル
    sh = OUT_DIR / "quarantine.sh"
    grave = args.graveyard.rstrip("/")
    cmds = [f'#!/usr/bin/env bash\nset -euo pipefail\nmkdir -p "{grave}"\n']
    for r in dead:
        # 実行痕跡がある or coverageあり は提案から除外（慎重）
        if r["runtime_seen"] or r["has_coverage"]:
            continue
        cmds.append(f'git mv "{r["path"]}" "{grave}/" || true')
    sh.write_text("\n".join(cmds) + "\n", encoding="utf-8")
    os.chmod(sh, 0o755)

    print("[OK] wrote:", rel(csv_path), rel(md_path), rel(sh))

if __name__ == "__main__":
    main()
