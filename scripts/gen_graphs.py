#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import json
import os
import shutil
import subprocess
import re
import time

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
GRAPHS = ROOT / "codex_reports" / "graphs"
CTXDIR = ROOT / "codex_reports" / "context"

DOT = GRAPHS / "imports.dot"
DOT_ALT = GRAPHS / "imports.gv"
SVG = GRAPHS / "imports.svg"
PNG = GRAPHS / "imports_preview.png"

CTX = CTXDIR / "context_pack.json"
ALLOWED = CTXDIR / "allowed_files.txt"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def _norm(p: Path) -> Path:
    try:
        return p.resolve()
    except Exception:
        return p.absolute()

def _samepath(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except FileNotFoundError:
        return False
    except Exception:
        return _norm(a) == _norm(b)

def _safe_copy(src: Path, dst: Path):
    if _samepath(src, dst):
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def _png_looks_suspicious(p: Path) -> bool:
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
            return (hist[0] / total > 0.95) or (hist[-1] / total > 0.95)
    except Exception:
        return False

# ------------------------------------------------------------
# Static roots discovery (with safety)
# ------------------------------------------------------------
STATIC_ROOTS: list[Path] = []
env_static = os.getenv("NOCTRIA_GUI_STATIC_DIR", "").strip()
if env_static:
    p = Path(env_static)
    if p.is_absolute() and p.exists() and not _samepath(p, ROOT) and ROOT not in p.parents:
        STATIC_ROOTS.append(_norm(p))

default_static = ROOT / "noctria_gui" / "static"
if default_static.exists() and not _samepath(default_static, ROOT):
    STATIC_ROOTS.append(_norm(default_static))

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

def _force_rankdir_tb(dot_src: Path) -> Path:
    """
    .dot 内に rankdir があれば TB に置換。無ければ先頭に rankdir=TB; を追加。
    一時ファイルを返す。
    """
    txt = dot_src.read_text(encoding="utf-8", errors="ignore")
    # 既存の rankdir=... を TB に置換（大小文字/空白/クォート対応）
    pattern = re.compile(r'(rankdir\s*=\s*")?(LR|RL|TB|BT)(")?', re.IGNORECASE)
    if "rankdir" in txt.lower():
        txt2 = re.sub(r'rankdir\s*=\s*("?)(LR|RL|TB|BT)\1', 'rankdir=TB', txt, flags=re.IGNORECASE)
    else:
        # digraph/graph の直後に rankdir=TB; を挿入
        m = re.search(r'^(digraph|graph)\s+[^{]*\{', txt, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            idx = m.end()
            txt2 = txt[:idx] + '\n  rankdir=TB;\n' + txt[idx:]
        else:
            txt2 = 'rankdir=TB;\n' + txt

    tmp = dot_src.with_name(f"._tmp_imports_tb_{int(time.time())}.dot")
    tmp.write_text(txt2, encoding="utf-8")
    return tmp

def build_svg_from_dot() -> bool:
    """
    Graphviz 'dot' で SVG を生成（縦レイアウト強制）。
    """
    dot_bin = shutil.which("dot")
    dot_file = _find_dot_file()
    if not dot_bin or not dot_file:
        if not dot_bin and dot_file:
            print("! graphviz 'dot' が見つかりません（sudo apt install graphviz 推奨）")
        return False

    SVG.parent.mkdir(parents=True, exist_ok=True)

    tmp_dot = _force_rankdir_tb(dot_file)
    cmd = [dot_bin, "-Tsvg", str(tmp_dot), "-o", str(SVG)]
    try:
        subprocess.run(cmd, check=True)
        print(f"+ built {SVG} from {dot_file.name} (forced rankdir=TB)")
        try:
            tmp_dot.unlink(missing_ok=True)
        except Exception:
            pass
        return True
    except subprocess.CalledProcessError as e:
        print(f"! dot failed: {e}")
        return False

def svg_to_png():
    """
    imports.svg -> imports_preview.png
    1) CairoSVG（白背景, 幅1200px）
    2) ダメ/怪しい時は rsvg-convert にフォールバック
    """
    if not SVG.exists():
        print("! missing imports.svg (skip PNG)")
        return

    PNG.parent.mkdir(parents=True, exist_ok=True)

    tried_cairo = False
    try:
        import cairosvg  # pip install cairosvg
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
    if not STATIC_ROOTS:
        print("! static ルートが見つからないためコピーはスキップ")
        return

    src_root = _norm(GRAPHS.parent)  # codex_reports
    for sroot in STATIC_ROOTS:
        dst_root = _norm(sroot / "codex_reports")

        if _samepath(dst_root, src_root):
            print(f"! skip sync: dst == src ({dst_root})")
            continue
        if src_root in dst_root.parents:
            print(f"! skip sync: dst is inside src ({dst_root})")
            continue

        for src_dir, _, files in os.walk(GRAPHS):
            src_dir = Path(src_dir)
            rel = src_dir.relative_to(GRAPHS)
            for f in files:
                _safe_copy(src_dir / f, dst_root / "graphs" / rel / f)

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
    built = build_svg_from_dot()   # 縦レイアウト強制でSVG再生成
    svg_to_png()                   # PNGプレビュー作成
    sync_to_static()               # staticに同期
    if SVG.exists():
        print(f"i SVG updated at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(SVG.stat().st_mtime))}")
