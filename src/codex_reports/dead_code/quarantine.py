#!/usr/bin/env python3
import csv, os, sys, subprocess, shlex
GRAVEYARD = sys.argv[1] if len(sys.argv)>1 else f"_graveyard"
CSV_PATH = "codex_reports/dead_code/report.csv"

def run(cmd): return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
def git_tracked(p): return run(f'git ls-files --error-unmatch -- {shlex.quote(p)}').returncode==0
def git_mv(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if git_tracked(src):
        r = run(f'git mv -f -- {shlex.quote(src)} {shlex.quote(dst)}')
        if r.returncode!=0:
            run(f'mv -f -- {shlex.quote(src)} {shlex.quote(dst)}')
            run(f'git add -A -- {shlex.quote(dst)}')
            run(f'git rm -f --cached -- {shlex.quote(src)} || true')
    else:
        if os.path.exists(src):
            run(f'mv -f -- {shlex.quote(src)} {shlex.quote(dst)}')
            run(f'git add -A -- {shlex.quote(dst)}')

print(f"[info] graveyard dir = {GRAVEYARD}")
os.makedirs(GRAVEYARD, exist_ok=True)

with open(CSV_PATH, newline="", encoding="utf-8") as f:
    rdr = csv.DictReader(f)
    for row in rdr:
        cats = (row.get("categories") or "")
        path = (row.get("path") or "").strip().strip('"')
        cov  = (row.get("has_coverage") or "0").strip()
        rts  = (row.get("runtime_seen") or "0").strip()

        if not path: continue
        if not any(k in cats for k in ("orphaned","unreferenced","unused_template")): continue
        if cov=="1" or rts=="1": continue
        if os.path.basename(path) == "__init__.py":
            print(f"[skip] {path} (__init__.py)"); continue

        dest = os.path.join(GRAVEYARD, path)
        if os.path.exists(dest):
            print(f"[skip] {path} (already moved)"); continue

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if git_tracked(path) or os.path.exists(path):
            git_mv(path, dest)
            print(f"[moved] {path} -> {dest}")
        else:
            print(f"[miss]  {path}")

print(f"[done] Quarantine completed into {GRAVEYARD}")
