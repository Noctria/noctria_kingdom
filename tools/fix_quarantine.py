#!/usr/bin/env python3
import csv, os, subprocess, sys, shlex

GRAVEYARD = sys.argv[sys.argv.index("--graveyard")+1] if "--graveyard" in sys.argv else "_graveyard"
CSV_PATH  = sys.argv[sys.argv.index("--csv")+1]       if "--csv" in sys.argv else "codex_reports/dead_code/report.csv"

def run(cmd):
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

def git_tracked(path:str)->bool:
    r = run(f'git ls-files --error-unmatch -- {shlex.quote(path)}')
    return r.returncode == 0

def git_mv(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if git_tracked(src):
        r = run(f'git mv -f -- {shlex.quote(src)} {shlex.quote(dst)}')
        if r.returncode!=0:
            # fallback mixed state
            run(f'mv -f -- {shlex.quote(src)} {shlex.quote(dst)}')
            run(f'git add -A -- {shlex.quote(dst)}')
            run(f'git rm -f --cached -- {shlex.quote(src)}')
    else:
        # plain FS move + stage
        if os.path.exists(src):
            run(f'mkdir -p {shlex.quote(os.path.dirname(dst))}')
            run(f'mv -f -- {shlex.quote(src)} {shlex.quote(dst)}')
            run(f'git add -A -- {shlex.quote(dst)}')

def relocate_flat_file(path:str):
    """_graveyard/2025-09-06/<basename> を _graveyard/2025-09-06/<full/path> に整列"""
    base = os.path.basename(path)
    flat = os.path.join(GRAVEYARD, base)
    dest = os.path.join(GRAVEYARD, path)
    if os.path.exists(flat) and not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        run(f'mv -f -- {shlex.quote(flat)} {shlex.quote(dest)}')
        run(f'git add -A -- {shlex.quote(dest)}')
        print(f'[rearranged] {flat} -> {dest}')

def move_if_needed(path:str):
    """まだ元の場所に残っていれば隔離"""
    if os.path.basename(path) == "__init__.py":
        # __init__.py は誤爆リスク大。今回はスキップ継続
        return
    dest = os.path.join(GRAVEYARD, path)
    if os.path.exists(dest):
        return
    if os.path.exists(path) or git_tracked(path):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        git_mv(path, dest)
        print(f'[moved] {path} -> {dest}')

# --- CSV読み込み（正しくヘッダ参照） ---
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    rdr = csv.DictReader(f)
    for row in rdr:
        categories = (row.get("categories") or "")
        path       = (row.get("path") or "").strip().strip('"')
        # coverage / runtime_seen が 0 のみが対象
        cov = (row.get("has_coverage") or "0").strip()
        rts = (row.get("runtime_seen") or "0").strip()
        if not path:
            continue
        if not any(k in categories for k in ("orphaned","unreferenced","unused_template")):
            continue
        if cov == "1" or rts == "1":
            continue

        # 1) フラット落ちの整列
        relocate_flat_file(path)
        # 2) まだ残ってるソースを隔離
        move_if_needed(path)

print(f'[done] fix_quarantine completed for {GRAVEYARD}')
