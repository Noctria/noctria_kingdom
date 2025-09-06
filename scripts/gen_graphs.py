#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import json, os, re, shutil, subprocess, time, xml.etree.ElementTree as ET

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
ROOT   = Path(__file__).resolve().parents[1]
GRAPHS = ROOT / "codex_reports" / "graphs"
CTXDIR = ROOT / "codex_reports" / "context"

DOT     = GRAPHS / "imports.dot"
DOT_ALT = GRAPHS / "imports.gv"
SVG     = GRAPHS / "imports.svg"
PNG     = GRAPHS / "imports_preview.png"

CTX     = CTXDIR / "context_pack.json"
ALLOWED = CTXDIR / "allowed_files.txt"

# ------------------------------------------------------------
# Options
# ------------------------------------------------------------
# _graveyard を隠す（1=隠す, 0=隠さない）
HIDE_GRAVEYARD = os.getenv("CODEX_HIDE_GRAVEYARD", "1") not in ("0", "false", "False")

# ------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------
def _norm(p: Path) -> Path:
    try: return p.resolve()
    except Exception: return p.absolute()

def _samepath(a: Path, b: Path) -> bool:
    try: return os.path.samefile(a, b)
    except FileNotFoundError: return False
    except Exception: return _norm(a) == _norm(b)

def _safe_copy(src: Path, dst: Path):
    if _samepath(src, dst): return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def _find_dot_file() -> Path | None:
    if DOT.exists(): return DOT
    if DOT_ALT.exists(): return DOT_ALT
    return None

# ------------------------------------------------------------
# DOT sanitization & filtering
# ------------------------------------------------------------
SANITIZE_RULES = [
    (r'(?i)\brankdir\s*=\s*(LR|RL)\b', 'rankdir=TB'),
    (r'(?i)\brankdir\s*=\s*"(LR|RL)"', 'rankdir=TB'),
    (r'(?i)\brank\s*=\s*same\b', ''),
    (r'(?i)\bconstraint\s*=\s*false\b', ''),
    (r'(?i)\bnewrank\s*=\s*true\b', ''),
    (r'(?i)\bpage\s*=\s*[^;\n]+', ''),
    (r'(?i)\bsize\s*=\s*[^;\n]+', ''),
    (r'(?i)\bratio\s*=\s*[^;\n]+', ''),
]

# _graveyard を含むノード/エッジ/サブグラフを除去
GRAVEYARD_PAT = re.compile(r'_graveyard', re.IGNORECASE)

def _strip_graveyard_blocks(text: str) -> str:
    """
    サブグラフやクラスタ名に _graveyard を含むブロックを波括弧レベルで丸ごと削除。
    （単純パーサ：DOTが標準的な整形である前提）
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        m = re.search(r'(subgraph\s+[^\{]*\{)|\{', text[i:], flags=re.IGNORECASE)
        if not m:
            out.append(text[i:])
            break
        start = i + m.start()
        brace = i + m.end() - 1  # '{' の位置
        header = text[i:start]
        head_str = text[start:brace]  # "subgraph cluster_x ..." or just whitespace before '{'

        # 直前の行に _graveyard が含まれる subgraph ならスキップ
        if GRAVEYARD_PAT.search(head_str):
            # 対応する '}' まで読み飛ばす
            depth = 0
            j = brace
            while j < n:
                if text[j] == '{': depth += 1
                elif text[j] == '}':
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            # header は残す（たとえば改行）
            out.append(header)
            i = j
        else:
            # 通常の '{' → そのまま1文字進めて続行
            out.append(text[i:brace+1])
            i = brace+1
    return ''.join(out)

def sanitize_dot(dot_src: Path) -> Path:
    txt = dot_src.read_text(encoding="utf-8", errors="ignore")

    # 1) _graveyard ノード/エッジの行を丸ごと除去
    if HIDE_GRAVEYARD:
        lines = txt.splitlines()
        kept = []
        for ln in lines:
            if GRAVEYARD_PAT.search(ln):
                # 行内に _graveyard がある → 基本スキップ
                continue
            kept.append(ln)
        txt = "\n".join(kept)
        # 2) _graveyard サブグラフ/クラスタをブロックごと削除
        txt = _strip_graveyard_blocks(txt)

    # 3) rankdir/constraint などをサニタイズ
    for pat, rep in SANITIZE_RULES:
        txt = re.sub(pat, rep, txt)

    # 4) digraph/graph 冒頭に安全な既定値を注入
    m = re.search(r'^(digraph|graph)\s+[^{]*\{', txt, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        i = m.end()
        inject = (
            '\n  rankdir=TB;\n'
            '  graph [overlap=false, splines=true, concentrate=true];\n'
            '  node  [shape=box, fontsize=10];\n'
            '  edge  [arrowsize=0.7];\n'
        )
        txt = txt[:i] + inject + txt[i:]

    tmp = dot_src.with_name(f"._tmp_sanitized_{int(time.time())}.dot")
    tmp.write_text(txt, encoding="utf-8")
    return tmp

# ------------------------------------------------------------
# SVG quality checks
# ------------------------------------------------------------
def _svg_aspect(svg_path: Path) -> float | None:
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        vb = root.attrib.get("viewBox", "")
        if vb:
            _, _, w, h = map(float, vb.split())
            return (w / h) if h else None
        w = root.attrib.get("width", "")
        h = root.attrib.get("height", "")
        if w.endswith(("pt","px")): w = w[:-2]
        if h.endswith(("pt","px")): h = h[:-2]
        return (float(w) / float(h)) if w and h else None
    except Exception:
        return None

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
            hist = im.histogram(); total = float(sum(hist)) or 1.0
            return (hist[0]/total > 0.95) or (hist[-1]/total > 0.95)
    except Exception:
        return False

# ------------------------------------------------------------
# Build graph images
# ------------------------------------------------------------
def build_svg_from_dot() -> bool:
    dot_bin = shutil.which("dot")
    dot_file = _find_dot_file()
    if not dot_bin or not dot_file:
        if not dot_bin and dot_file:
            print("! graphviz 'dot' が見つかりません（sudo apt install graphviz 推奨）")
        return False

    SVG.parent.mkdir(parents=True, exist_ok=True)

    tmp = sanitize_dot(dot_file)
    cmd = [dot_bin, "-Tsvg",
           "-Grankdir=TB", "-Gnodesep=0.45", "-Granksep=0.7",
           str(tmp), "-o", str(SVG)]
    try:
        subprocess.run(cmd, check=True)
        print(f"+ built {SVG} from {dot_file.name} (sanitized + TB{' + hide_graveyard' if HIDE_GRAVEYARD else ''})")
    except subprocess.CalledProcessError as e:
        print(f"! dot failed: {e}")
        return False
    finally:
        try: tmp.unlink(missing_ok=True)
        except Exception: pass

    aspect = _svg_aspect(SVG) or 9.99
    if aspect > 2.6:
        sfdp = shutil.which("sfdp")
        if sfdp:
            try:
                subprocess.run([sfdp, "-Tsvg", str(dot_file), "-o", str(SVG)], check=True)
                print("+ rebuilt via sfdp (fallback)")
                aspect = _svg_aspect(SVG) or aspect
            except subprocess.CalledProcessError as e:
                print(f"! sfdp failed: {e}")
        if aspect > 2.6:
            twopi = shutil.which("twopi")
            if twopi:
                try:
                    subprocess.run([twopi, "-Tsvg", str(dot_file), "-o", str(SVG)], check=True)
                    print("+ rebuilt via twopi (fallback)")
                except subprocess.CalledProcessError as e:
                    print(f"! twopi failed: {e}")
    return True

def svg_to_png():
    if not SVG.exists():
        print("! missing imports.svg (skip PNG)"); return
    PNG.parent.mkdir(parents=True, exist_ok=True)
    tried_cairo = False
    try:
        import cairosvg
        cairosvg.svg2png(url=str(SVG), write_to=str(PNG), output_width=1200, background_color="white")
        tried_cairo = True
        print(f"+ wrote {PNG} via CairoSVG")
    except Exception as e:
        print(f"! CairoSVG failed: {e}")
    if (not PNG.exists()) or _png_looks_suspicious(PNG):
        rsvg = shutil.which("rsvg-convert")
        if rsvg:
            try:
                subprocess.run([rsvg, "-w", "1200", "-o", str(PNG), str(SVG)], check=True)
                print(f"+ wrote {PNG} via rsvg-convert (fallback)")
            except subprocess.CalledProcessError as e:
                print(f"! rsvg-convert failed: {e}")
        elif tried_cairo:
            print("! PNG looks suspicious and librsvg is unavailable; keeping CairoSVG output")

# ------------------------------------------------------------
# Context & static sync
# ------------------------------------------------------------
def ensure_context():
    CTXDIR.mkdir(parents=True, exist_ok=True)
    if not CTX.exists():
        CTX.write_text(json.dumps({
            "version": 1, "generated_at": "scripts/gen_graphs.py",
            "modules": {}, "adjacency": {}, "tests_map": {},
            "allowlist_roots": ["src/"], "banned_paths": [], "critical_files": []
        }, ensure_ascii=False, indent=2)); print(f"+ wrote {CTX}")
    if not ALLOWED.exists():
        ALLOWED.write_text("src/\n"); print(f"+ wrote {ALLOWED}")

def _discover_static_roots() -> list[Path]:
    roots: list[Path] = []
    env_static = os.getenv("NOCTRIA_GUI_STATIC_DIR", "").strip()
    if env_static:
        p = Path(env_static)
        if p.is_absolute() and p.exists() and not _samepath(p, ROOT) and ROOT not in p.parents:
            roots.append(_norm(p))
    default_static = ROOT / "noctria_gui" / "static"
    if default_static.exists() and not _samepath(default_static, ROOT):
        roots.append(_norm(default_static))
    seen=set(); return [p for p in roots if not (str(p) in seen or seen.add(str(p)))]

def sync_to_static():
    STATIC_ROOTS = _discover_static_roots()
    if not STATIC_ROOTS:
        print("! static ルートが見つからないためコピーはスキップ"); return
    src_root = _norm(GRAPHS.parent)
    for sroot in STATIC_ROOTS:
        dst_root = _norm(sroot / "codex_reports")
        if _samepath(dst_root, src_root) or (src_root in dst_root.parents):
            print(f"! skip sync: invalid dst ({dst_root})"); continue
        for src_dir, _, files in os.walk(GRAPHS):
            sd = Path(src_dir); rel = sd.relative_to(GRAPHS)
            for f in files: _safe_copy(sd / f, dst_root / "graphs" / rel / f)
        for src_dir, _, files in os.walk(CTXDIR):
            sd = Path(src_dir); rel = sd.relative_to(CTXDIR)
            for f in files: _safe_copy(sd / f, dst_root / "context" / rel / f)
        print(f"+ synced codex_reports -> {dst_root}")

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
if __name__ == "__main__":
    ensure_context()
    build_svg_from_dot()
    svg_to_png()
    sync_to_static()
    if SVG.exists():
        print(f"i SVG updated at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(SVG.stat().st_mtime))}")
