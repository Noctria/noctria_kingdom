#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import json, os, re, shutil, subprocess, time, xml.etree.ElementTree as ET

# ============== Paths ==============
ROOT   = Path(__file__).resolve().parents[1]
GRAPHS = ROOT / "codex_reports" / "graphs"
CTXDIR = ROOT / "codex_reports" / "context"

DOT     = GRAPHS / "imports.dot"
DOT_ALT = GRAPHS / "imports.gv"
SVG     = GRAPHS / "imports.svg"
PNG     = GRAPHS / "imports_preview.png"

CTX     = CTXDIR / "context_pack.json"
ALLOWED = CTXDIR / "allowed_files.txt"

# ============== Options ==============
# 1= _graveyard を完全に隠す, 0=隠さない
HIDE_GRAVEYARD = os.getenv("CODEX_HIDE_GRAVEYARD", "1") not in ("0", "false", "False")

# ============== Helpers ==============
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

# ============== SVG quality checks ==============
def _svg_aspect(svg_path: Path) -> float | None:
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        vb = root.attrib.get("viewBox", "")
        if vb:
            _, _, w, h = map(float, vb.split())
            return (w / h) if h else None
        w = root.attrib.get("width", ""); h = root.attrib.get("height", "")
        for s in ("pt","px"): w = w[:-len(s)] if w.endswith(s) else w
        for s in ("pt","px"): h = h[:-len(s)] if h.endswith(s) else h
        return (float(w)/float(h)) if w and h else None
    except Exception:
        return None

def _png_looks_suspicious(p: Path) -> bool:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return False
    if not p.exists() or p.stat().st_size < 2_000:  # too tiny
        return True
    try:
        with Image.open(p) as im:
            im = im.convert("L")
            hist = im.histogram(); total = float(sum(hist)) or 1.0
            return (hist[0]/total > 0.95) or (hist[-1]/total > 0.95)
    except Exception:
        return False

# ============== DOT filtering (safe) ==============
_GRAVEYARD = re.compile(r"_graveyard", re.IGNORECASE)

def _filter_with_pydot(src: Path) -> tuple[Path, int]:
    """pydot でDOTを読み、_graveyard を含むノード/エッジ/サブグラフを完全除去。"""
    import pydot  # type: ignore

    graphs = pydot.graph_from_dot_file(str(src))
    if not graphs:
        raise RuntimeError("pydot failed to parse DOT")

    g: pydot.Dot = graphs[0]
    # 新しいグラフを同種で作成（有向/無向の別を維持）
    new = pydot.Dot(graph_type=g.get_type() or "digraph")
    # グラフ属性を継承
    for k, v in g.get_attributes().items():
        new.set(k, v)

    # subgraphs：_graveyard を含む名前は丸ごとスキップ
    keep_subgraphs = []
    for sg in g.get_subgraphs():
        name = (sg.get_name() or "").strip('"')
        if _GRAVEYARD.search(name):
            continue
        keep_subgraphs.append(sg)

    # ノードセット
    keep_nodes: dict[str, pydot.Node] = {}
    for n in g.get_nodes():
        name = (n.get_name() or "").strip('"')
        # pydot は "node","graph","edge" という擬似ノードを含むことがあるので除外
        if name in ("node", "graph", "edge"):
            continue
        if _GRAVEYARD.search(name):
            continue
        keep_nodes[name] = n

    # サブグラフ内のノードも拾う
    for sg in keep_subgraphs:
        for n in sg.get_nodes():
            name = (n.get_name() or "").strip('"')
            if name in ("node","graph","edge"): continue
            if _GRAVEYARD.search(name): continue
            keep_nodes[name] = n

    # 新グラフへノード追加
    for n in keep_nodes.values():
        new.add_node(n)

    # エッジ：端点が両方 keep に含まれるものだけ移植
    kept_edges = 0
    for e in g.get_edges():
        s = (e.get_source() or "").strip('"')
        t = (e.get_destination() or "").strip('"')
        if _GRAVEYARD.search(s) or _GRAVEYARD.search(t):
            continue
        if s in keep_nodes and t in keep_nodes:
            new.add_edge(e); kept_edges += 1
    # サブグラフに関しては、「丸ごと除去」の方針なので追加はしない

    # 仕上げ：rankdir=TB を強制（属性上書き）
    new.set("rankdir", "TB")
    # 適度に間隔
    new.set("nodesep", "0.45")
    new.set("ranksep", "0.70")
    # 線滑らか
    new.set("overlap", "false")
    new.set("splines", "true")
    new.set("concentrate", "true")

    out = src.with_name(f"._tmp_filtered_{int(time.time())}.dot")
    new.write(out, format="raw")
    return out, len(keep_nodes)

def _filter_with_text(src: Path) -> tuple[Path, int]:
    """
    pydot が無いときの保守的フィルタ：
    - subgraph ヘッダに _graveyard を含むブロックだけ {} バランスで削除
    - 行単位で _graveyard を含むノード/エッジ定義を削除
    """
    txt = src.read_text(encoding="utf-8", errors="ignore")

    # subgraph ... { ブロック削除
    out, i, n = [], 0, len(txt)
    while i < n:
        m = re.search(r'\bsubgraph\b[^{]*\{', txt[i:], flags=re.IGNORECASE)
        if not m:
            out.append(txt[i:]); break
        start = i + m.start()
        brace = i + m.end() - 1  # '{'
        header = txt[start:brace]
        if _GRAVEYARD.search(header):
            depth, j = 1, brace + 1
            while j < n and depth > 0:
                c = txt[j]
                if c == '{': depth += 1
                elif c == '}': depth -= 1
                j += 1
            out.append(txt[i:start])  # ヘッダ前までは保持
            i = j
        else:
            out.append(txt[i:brace+1]); i = brace + 1
    txt = ''.join(out)

    # 行単位フィルタ（ノード/エッジらしい行のみ）
    kept, keep_nodes = [], set()
    for ln in txt.splitlines():
        if _GRAVEYARD.search(ln):
            if '->' in ln or '--' in ln or '[' in ln or ']' in ln or ';' in ln:
                continue  # 定義っぽい行は捨てる
        kept.append(ln)
        # 雑にノード名っぽいものを拾って数える（見積もり用）
        m = re.match(r'\s*"?(?P<id>[\w\.:/\\-]+)"?\s*(\[|;)', ln)
        if m:
            keep_nodes.add(m.group("id"))
    out_txt = "\n".join(kept)

    # graph 冒頭に既定値を注入
    m = re.search(r'^(digraph|graph)\s+[^{]*\{', out_txt, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        i = m.end()
        inject = (
            '\n  rankdir=TB;\n'
            '  graph [overlap=false, splines=true, concentrate=true, nodesep=0.45, ranksep=0.70];\n'
            '  node  [shape=box, fontsize=10];\n'
            '  edge  [arrowsize=0.7];\n'
        )
        out_txt = out_txt[:i] + inject + out_txt[i:]

    out = src.with_name(f"._tmp_filtered_{int(time.time())}.dot")
    out.write_text(out_txt, encoding="utf-8")
    return out, len(keep_nodes)

def make_filtered_dot(src: Path, hide_graveyard: bool) -> tuple[Path, int, bool]:
    """
    return: (filtered_dot_path, kept_node_count, used_pydot)
    """
    if not hide_graveyard:
        return src, -1, False
    try:
        import pydot  # noqa
        filtered, n = _filter_with_pydot(src)
        return filtered, n, True
    except Exception as e:
        print(f"! pydot unavailable or failed ({e}); fallback to text filter")
        filtered, n = _filter_with_text(src)
        return filtered, n, False

# ============== Build / Convert ==============
def build_svg_from_dot() -> bool:
    dot_bin = shutil.which("dot")
    dot_file = _find_dot_file()
    if not dot_bin or not dot_file:
        if not dot_bin and dot_file:
            print("! graphviz 'dot' が見つかりません（sudo apt install graphviz 推奨）")
        return False

    SVG.parent.mkdir(parents=True, exist_ok=True)

    # フィルタ（_graveyard 完全非表示）
    filtered_dot, kept_nodes, used_pydot = make_filtered_dot(dot_file, HIDE_GRAVEYARD)

    def _run_dot(src_dot: Path):
        cmd = [dot_bin, "-Tsvg", "-Grankdir=TB", "-Gnodesep=0.45", "-Granksep=0.70",
               str(src_dot), "-o", str(SVG)]
        subprocess.run(cmd, check=True)

    try:
        _run_dot(filtered_dot)
        tag = "hide_graveyard+pydot" if (HIDE_GRAVEYARD and used_pydot) else ("hide_graveyard" if HIDE_GRAVEYARD else "no_hide")
        print(f"+ built {SVG} from {dot_file.name} ({tag})")
    except subprocess.CalledProcessError as e:
        print(f"! dot failed: {e}")
        return False
    finally:
        # 一時ファイルの掃除
        if filtered_dot is not dot_file:
            try: filtered_dot.unlink(missing_ok=True)
            except Exception: pass

    # 仕上げの健全性チェック：空や異常に横長なら「非隠蔽」で作り直す
    aspect = _svg_aspect(SVG)
    too_tiny = SVG.stat().st_size < 10_000
    too_wide = (aspect is not None and aspect > 5.0)
    too_few  = (HIDE_GRAVEYARD and kept_nodes >= 0 and kept_nodes < 5)
    if too_tiny or too_wide or too_few:
        if HIDE_GRAVEYARD:
            print("! filtered graph looks degenerate → rebuilding WITHOUT graveyard")
            tmp_dot, _, _ = make_filtered_dot(dot_file, hide_graveyard=False)
            try:
                _run_dot(tmp_dot)
                print("+ rebuilt without graveyard filtering")
            finally:
                if tmp_dot is not dot_file:
                    try: tmp_dot.unlink(missing_ok=True)
                    except Exception: pass
        else:
            # 最後の砦：sfdp / twopi フォールバック
            sfdp = shutil.which("sfdp")
            if sfdp:
                try:
                    subprocess.run([sfdp, "-Tsvg", str(dot_file), "-o", str(SVG)], check=True)
                    print("+ rebuilt via sfdp (fallback)")
                except subprocess.CalledProcessError:
                    pass
            twopi = shutil.which("twopi")
            if twopi:
                try:
                    subprocess.run([twopi, "-Tsvg", str(dot_file), "-o", str(SVG)], check=True)
                    print("+ rebuilt via twopi (fallback)")
                except subprocess.CalledProcessError:
                    pass

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

# ============== Context & static sync ==============
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

# ============== Main ==============
if __name__ == "__main__":
    ensure_context()
    build_svg_from_dot()
    svg_to_png()
    sync_to_static()
    if SVG.exists():
        print(f"i SVG updated at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(SVG.stat().st_mtime))}")
