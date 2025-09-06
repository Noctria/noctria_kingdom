#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
GRAPHS = ROOT / "codex_reports" / "graphs"
CTXDIR = ROOT / "codex_reports" / "context"
SVG = GRAPHS / "imports.svg"
PNG = GRAPHS / "imports_preview.png"
CTX = CTXDIR / "context_pack.json"
ALLOWED = CTXDIR / "allowed_files.txt"

# 静的配信用（存在すればコピー）
STATIC_ROOTS = [
    ROOT / "noctria_gui" / "static",
    Path(os.getenv("NOCTRIA_GUI_STATIC_DIR", "")),
]
STATIC_ROOTS = [p for p in STATIC_ROOTS if p and p.exists()]

def svg_to_png():
    try:
        import cairosvg  # pip install cairosvg
    except Exception:
        print("! cairosvg 未導入のため PNG 生成はスキップ")
        return
    if SVG.exists():
        PNG.parent.mkdir(parents=True, exist_ok=True)
        cairosvg.svg2png(url=str(SVG), write_to=str(PNG), output_width=1200)
        print(f"+ wrote {PNG}")
    else:
        print("! missing imports.svg (skip PNG)")

def ensure_context():
    CTXDIR.mkdir(parents=True, exist_ok=True)
    if not CTX.exists():
        CTX.write_text(json.dumps({
            "version": 1,
            "generated_at": "scripts/gen_graphs.py",
            "modules": {}, "adjacency": {}, "tests_map": {},
            "allowlist_roots": ["src/"], "banned_paths": [], "critical_files": []
        }, ensure_ascii=False, indent=2))
        print(f"+ wrote {CTX}")
    if not ALLOWED.exists():
        ALLOWED.write_text("src/\n")
        print(f"+ wrote {ALLOWED}")

def sync_to_static():
    """codex_reports を static 下に見えるようにコピー（最小運用）"""
    if not STATIC_ROOTS:
        print("! static ルートが見つからないためコピーはスキップ")
        return
    for sroot in STATIC_ROOTS:
        dst = sroot / "codex_reports"
        if dst.exists():
            # 既存を最小上書きコピー
            for src_dir, _, files in os.walk(GRAPHS):
                rel = Path(src_dir).relative_to(GRAPHS)
                (dst / "graphs" / rel).mkdir(parents=True, exist_ok=True)
                for f in files:
                    shutil.copy2(Path(src_dir) / f, dst / "graphs" / rel / f)
            for src_dir, _, files in os.walk(CTXDIR):
                rel = Path(src_dir).relative_to(CTXDIR)
                (dst / "context" / rel).mkdir(parents=True, exist_ok=True)
                for f in files:
                    shutil.copy2(Path(src_dir) / f, dst / "context" / rel / f)
        else:
            shutil.copytree(GRAPHS.parent, dst, dirs_exist_ok=True)
        print(f"+ synced codex_reports -> {dst}")

if __name__ == "__main__":
    ensure_context()
    svg_to_png()
    sync_to_static()
