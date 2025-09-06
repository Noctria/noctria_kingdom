#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import json
import os
import shutil

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
GRAPHS = ROOT / "codex_reports" / "graphs"
CTXDIR = ROOT / "codex_reports" / "context"
SVG = GRAPHS / "imports.svg"
PNG = GRAPHS / "imports_preview.png"
CTX = CTXDIR / "context_pack.json"
ALLOWED = CTXDIR / "allowed_files.txt"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _norm(p: Path) -> Path:
    """Resolve to an absolute, canonical path if possible."""
    try:
        return p.resolve()
    except Exception:
        return p.absolute()

def _samepath(a: Path, b: Path) -> bool:
    """Return True if a and b refer to the same file/dir."""
    try:
        return os.path.samefile(a, b)
    except FileNotFoundError:
        return False
    except Exception:
        return _norm(a) == _norm(b)

def _safe_copy(src: Path, dst: Path):
    """Copy src -> dst if they are not the same file."""
    if _samepath(src, dst):
        # Avoid SameFileError when dst is the same as src
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

# ------------------------------------------------------------
# Static roots discovery (with safety)
# - skip empty/relative paths
# - skip roots that are the same as the repo root
# - skip roots inside the source tree to avoid copying onto itself
# ------------------------------------------------------------
STATIC_ROOTS: list[Path] = []

# Env override (absolute, existing, and not the repo itself/inside repo)
env_static = os.getenv("NOCTRIA_GUI_STATIC_DIR", "").strip()
if env_static:
    p = Path(env_static)
    if p.is_absolute() and p.exists() and not _samepath(p, ROOT) and ROOT not in p.parents:
        STATIC_ROOTS.append(_norm(p))

# Default static dir: noctria_gui/static (if exists and safe)
default_static = ROOT / "noctria_gui" / "static"
if default_static.exists() and not _samepath(default_static, ROOT):
    STATIC_ROOTS.append(_norm(default_static))

# Deduplicate while preserving order
_seen = set()
STATIC_ROOTS = [p for p in STATIC_ROOTS if not (str(p) in _seen or _seen.add(str(p)))]

# ------------------------------------------------------------
# Actions
# ------------------------------------------------------------
def svg_to_png():
    """Convert imports.svg -> imports_preview.png (optional if cairosvg exists)."""
    try:
        import cairosvg  # pip install cairosvg (recommended in venv)
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
    """Ensure minimal context files exist."""
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
    """
    Copy codex_reports to each static root.
    - Skips when destination equals source or is inside source
    - Avoids SameFileError by using _safe_copy
    """
    if not STATIC_ROOTS:
        print("! static ルートが見つからないためコピーはスキップ")
        return

    src_root = _norm(GRAPHS.parent)  # codex_reports (source)
    for sroot in STATIC_ROOTS:
        dst_root = _norm(sroot / "codex_reports")

        # Safety: skip if dst == src or dst is inside src (would copy onto itself)
        if _samepath(dst_root, src_root):
            print(f"! skip sync: dst == src ({dst_root})")
            continue
        if src_root in dst_root.parents:
            print(f"! skip sync: dst is inside src ({dst_root})")
            continue

        # Copy graphs
        for src_dir, _, files in os.walk(GRAPHS):
            src_dir = Path(src_dir)
            rel = src_dir.relative_to(GRAPHS)
            for f in files:
                _safe_copy(src_dir / f, dst_root / "graphs" / rel / f)

        # Copy context
        for src_dir, _, files in os.walk(CTXDIR):
            src_dir = Path(src_dir)
            rel = src_dir.relative_to(CTXDIR)
            for f in files:
                _safe_copy(src_dir / f, dst_root / "context" / rel / f)

        print(f"+ synced codex_reports -> {dst_root}")

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
if __name__ == "__main__":
    ensure_context()
    svg_to_png()
    sync_to_static()
