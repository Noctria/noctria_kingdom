#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import json
import os
import shutil
import subprocess

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
GRAPHS = ROOT / "codex_reports" / "graphs"
CTXDIR = ROOT / "codex_reports" / "context"

# graph artifacts
DOT = GRAPHS / "imports.dot"          # 優先
DOT_ALT = GRAPHS / "imports.gv"       # 代替
SVG = GRAPHS / "imports.svg"
PNG = GRAPHS / "imports_preview.png"

# context files
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
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def _png_looks_suspicious(p: Path) -> bool:
    """
    軽い健全性チェック:
      - 0バイト/極小サイズ
      - ほぼ単色（真っ黒/真っ白）に近い
    Pillowが無ければチェックスキップ（False）。
    """
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return False

    if not p.exists() or p.stat().st_size < 2_000:
        return True

    try:
        with Image.open(p) as im:
            im = im.convert("L")
            hist = im.histogram()
            total = float(sum(hist)) or 1.0
            share_black = hist[0] / total
            share_white = hist[-1] / total
            return (share_black > 0.95) or (share_white > 0.95)
    except Exception:
        return False

# ------------------------------------------------------------
# Static roots discovery (with safety)
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
# Build / Convert
# ------------------------------------------------------------
def _find_dot_file() -> Path | None:
    if DOT.exists():
        return DOT
    if DOT_ALT.exists():
        return DOT_ALT
    return None

def build_svg_from_dot(rankdir: str = "TB") -> bool:
    """
    .dot/.gv がある場合に Graphviz `dot` で SVG を生成（縦レイアウト: rankdir=TB）。
    生成できたら True を返す。`dot` 未導入や .dot 不在なら False。
    """
    dot_bin = shutil.which("dot")
    dot_file = _find_dot_file()
    if not dot_bin or not dot_file:
        # dot 未導入 or dot ファイル無し → 既存の SVG をそのまま使う
        if not dot_bin and dot_file:
            print("! graphviz 'dot' が見つかりません（apt install graphviz 推奨）")
        return False

    SVG.parent.mkdir(parents=True, exist_ok=True)
    cmd = [dot_bin, "-Tsvg", f"-Grankdir={rankdir}", str(dot_file), "-o", str(SVG)]
    try:
        subprocess.run(cmd, check=True)
        print(f"+ built {SVG} from {dot_file.name} with rankdir={rankdir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"! dot failed: {e}")
        return False

def svg_to_png():
    """
    Convert imports.svg -> imports_preview.png
    1) CairoSVG（白背景, 幅1200px）で出力
    2) 結果が怪しければ rsvg-convert にフォールバック（存在すれば）
    """
    if not SVG.exists():
        print("! missing imports.svg (skip PNG)")
        return

    PNG.parent.mkdir(parents=True, exist_ok=True)

    # --- try CairoSVG first (white background) ---
    tried_cairo = False
    try:
        import cairosvg  # pip install cairosvg (recommended in venv)
        cairosvg.svg2png(
            url=str(SVG),
            write_to=str(PNG),
            output_width=1200,
            background_color="white",
        )
        tried_cairo = True
        print(f"+ wrote {PNG} via CairoSVG")
    except Exception as e:
        print(f"! CairoSVG failed: {e}")

    # --- sanity check; fallback if needed ---
    need_fallback = (not PNG.exists()) or _png_looks_suspicious(PNG)
    if need_fallback:
        rsvg = shutil.which("rsvg-convert")
        if rsvg:
            try:
                subprocess.run([rsvg, "-w", "1200", "-o", str(PNG), str(SVG)], check=True)
                print(f"+ wrote {PNG} via rsvg-convert (fallback)")
                return
            except subprocess.CalledProcessError as e:
                print(f"! rsvg-convert failed: {e}")
        else:
            if tried_cairo:
                print("! PNG looks suspicious and librsvg is unavailable; keeping CairoSVG output")
            else:
                print("! no exporter worked; PNG not generated")

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
    # 1) .dot/.gv があれば縦レイアウトで SVG 再生成（なければ既存 SVG を利用）
    built = build_svg_from_dot(rankdir="TB")
    # 2) SVG → PNG（プレビュー用）
    svg_to_png()
    # 3) static に同期
    sync_to_static()
