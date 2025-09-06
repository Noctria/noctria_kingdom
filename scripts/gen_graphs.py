#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import json, os, re, shutil, subprocess, time, xml.etree.ElementTree as ET
from collections import defaultdict, deque

# ================== Paths ==================
ROOT   = Path(__file__).resolve().parents[1]
GRAPHS = ROOT / "codex_reports" / "graphs"
CTXDIR = ROOT / "codex_reports" / "context"

DOT     = GRAPHS / "imports.dot"
DOT_ALT = GRAPHS / "imports.gv"
SVG     = GRAPHS / "imports.svg"
PNG     = GRAPHS / "imports_preview.png"

CTX     = CTXDIR / "context_pack.json"
ALLOWED = CTXDIR / "allowed_files.txt"

# ================== Options ==================
# _graveyard を完全に隠す（デフォルトON）
HIDE_GRAVEYARD = os.getenv("CODEX_HIDE_GRAVEYARD", "1") not in ("0","false","False")
# フィルタバックエンド（"text" 推奨）
FILTER_BACKEND = os.getenv("CODEX_FILTER_BACKEND", "text").lower().strip()
# レイヤリングバックエンド：text（正規表現でエッジ抽出して rank=same 段組を付与）
LAYER_BACKEND  = os.getenv("CODEX_LAYER_BACKEND", "text").lower().strip()  # 'text' or ''
# viewport（任意）例: 1000,4000,1.0
FORCE_VIEWPORT = os.getenv("CODEX_FORCE_VIEWPORT", "").strip()

# ================== Helpers ==================
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

# ================== SVG checks ==================
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
    if not p.exists() or p.stat().st_size < 2_000:
        return True
    try:
        with Image.open(p) as im:
            im = im.convert("L")
            hist = im.histogram(); tot = float(sum(hist)) or 1.0
            return (hist[0]/tot > 0.95) or (hist[-1]/tot > 0.95)
    except Exception:
        return False

# ================== Filtering (_graveyard) ==================
_GRAVEYARD = re.compile(r"_graveyard", re.IGNORECASE)

def _filter_with_text(src: Path) -> tuple[str, int]:
    """subgraph名に _graveyard を含むブロック丸ごと削除 + 行単位で _graveyard を含む定義を削除"""
    txt = src.read_text(encoding="utf-8", errors="ignore")

    # subgraph ... { ... } をバランス取りで削除
    out, i, n = [], 0, len(txt)
    while i < n:
        m = re.search(r'\bsubgraph\b[^{]*\{', txt[i:], flags=re.IGNORECASE)
        if not m:
            out.append(txt[i:]); break
        start = i + m.start()
        brace = i + m.end() - 1
        header = txt[start:brace]
        if _GRAVEYARD.search(header):
            depth, j = 1, brace + 1
            while j < n and depth > 0:
                c = txt[j]
                if c == '{': depth += 1
                elif c == '}': depth -= 1
                j += 1
            out.append(txt[i:start])  # ヘッダ前は保持
            i = j
        else:
            out.append(txt[i:brace+1]); i = brace + 1
    txt = ''.join(out)

    kept, node_names = [], set()
    for ln in txt.splitlines():
        if _GRAVEYARD.search(ln):
            if '->' in ln or '--' in ln or '[' in ln or ']' in ln or ';' in ln:
                continue
        kept.append(ln)
        m = re.match(r'\s*"?(?P<id>[\w\.:/\\-]+)"?\s*(\[|;)', ln)
        if m: node_names.add(m.group("id"))
    body = "\n".join(kept)

    # 冒頭に既定値（“縦寄せ”向け）
    m = re.search(r'^(digraph|graph)\s+[^{]*\{', body, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        j = m.end()
        inject = (
            '\n  rankdir=TB;\n'
            '  graph [overlap=false, splines=true, concentrate=true, '
            '         nodesep=0.35, ranksep=0.70, ratio=compress, '
            '         margin="0,0", pack=true, packmode=graph];\n'
            '  node  [shape=box, fontsize=10];\n'
            '  edge  [arrowsize=0.7];\n'
        )
        body = body[:j] + inject + body[j:]
    return body, len(node_names)

def make_filtered_text(src: Path, hide_graveyard: bool) -> tuple[Path, int]:
    if not hide_graveyard:
        return src, -1
    body, n = _filter_with_text(src)
    out = src.with_name(f"._tmp_filtered_{int(time.time())}.dot")
    out.write_text(body, encoding="utf-8")
    return out, n

# ================== Layering (text backend) ==================
_EDGE_RE = re.compile(
    r'(?P<lhs>"[^"]+"|[^\s\[\];]+)\s*->\s*(?P<rhs>"[^"]+"|[^\s\[\];]+)'
)

def _strip_id(s: str) -> str:
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s.strip('<>')  # HTML-like 名残をざっくり除去

def _build_layers_from_edges(dot_text: str) -> tuple[list[list[str]], set[tuple[str,str]]]:
    """DOTテキストから A->B を抽出して、Kahn法でレイヤ（rank）割当て"""
    edges: set[tuple[str,str]] = set()
    nodes: set[str] = set()
    for m in _EDGE_RE.finditer(dot_text):
        a = _strip_id(m.group('lhs')); b = _strip_id(m.group('rhs'))
        if not a or not b: continue
        edges.add((a, b))
        nodes.add(a); nodes.add(b)

    if not nodes:
        return [], set()

    indeg = {u: 0 for u in nodes}
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        indeg[b] += 1

    layers: list[list[str]] = []
    rem = set(nodes)
    q = deque(sorted([u for u in rem if indeg[u] == 0]))
    while rem:
        if not q:
            # サイクル: 入次数最小を拾って次レイヤへ
            pick = min(rem, key=lambda u: indeg[u])
            q.append(pick)
        this = []
        seen = set()
        while q:
            u = q.popleft()
            if u in seen or u not in rem:
                continue
            seen.add(u)
            this.append(u)
        if not this:
            break
        for u in this:
            rem.remove(u)
            for v in adj[u]:
                indeg[v] = max(0, indeg[v]-1)
        # 次レイヤ候補
        nextq = deque(sorted([u for u in rem if indeg[u] == 0]))
        q = nextq
        layers.append(this)

    # もし残りがあれば最後のレイヤに付ける（強引に段を作る）
    if rem:
        layers.append(sorted(rem))
    return layers, edges

def _wrap_layered_dot(original_text: str) -> str:
    """元DOTの属性セットを活かしつつ、rank=same の段組 subgraph を追記して返す"""
    layers, edges = _build_layers_from_edges(original_text)
    # グラフヘッダを抽出
    m = re.search(r'^(digraph|graph)\s+[^{]*\{', original_text, flags=re.IGNORECASE | re.MULTILINE)
    if not m or not layers:
        return original_text  # 何もしない

    head_end = m.end()
    head = original_text[:head_end]
    tail = original_text[head_end:]
    # 既定属性（重複注入を避けるが、二重でもGraphvizは大抵大丈夫）
    attrs = (
        '\n  rankdir=TB;\n'
        '  graph [overlap=false, splines=true, concentrate=true, '
        '         nodesep=0.35, ranksep=0.80, ratio=compress, '
        '         margin="0,0", pack=true, packmode=graph];\n'
        '  node  [shape=box, fontsize=10];\n'
        '  edge  [arrowsize=0.7];\n'
    )
    buf = [head, attrs]
    # 段組 subgraph
    for i, layer in enumerate(layers):
        if not layer: 
            continue
        buf.append(f'  subgraph "cluster_rank_{i}" {{ rank=same;')
        for u in layer:
            # ノードの再宣言（存在しなくてもOK）
            buf.append(f'    "{u}";')
        buf.append('  }\n')
    # エッジは元DOTにもあるが、足りない場合に備え追記（重複OK）
    for a, b in edges:
        buf.append(f'  "{a}" -> "{b}";\n')

    # 残り本文（オリジナル）と合わせて閉じる
    buf.append(tail)
    return ''.join(buf)

def make_layered_text(filtered_dot_path: Path) -> Path:
    txt = filtered_dot_path.read_text(encoding="utf-8", errors="ignore")
    layered = _wrap_layered_dot(txt)
    out = filtered_dot_path.with_name(f"._tmp_layered_{int(time.time())}.dot")
    out.write_text(layered, encoding="utf-8")
    return out

# ================== Build / Convert ==================
def build_svg_from_dot() -> bool:
    dot_bin = shutil.which("dot")
    dot_file = _find_dot_file()
    if not dot_bin or not dot_file:
        if not dot_bin and dot_file:
            print("! graphviz 'dot' が見つかりません（sudo apt install graphviz 推奨）")
        return False

    SVG.parent.mkdir(parents=True, exist_ok=True)

    # 1) フィルタ（_graveyard）
    if FILTER_BACKEND == "text":
        filtered_dot, kept_nodes = make_filtered_text(dot_file, HIDE_GRAVEYARD)
        used_backend = "text"
    else:
        # 既定は text
        filtered_dot, kept_nodes = make_filtered_text(dot_file, HIDE_GRAVEYARD)
        used_backend = "text"

    # 2) レイヤリング（textバックエンド）
    if LAYER_BACKEND == "text":
        try:
            layered_dot = make_layered_text(filtered_dot)
            src_for_dot = layered_dot
            layer_tag = "+layered(text)"
        except Exception as e:
            print(f"! text layering failed ({e}); fallback to filtered only")
            src_for_dot = filtered_dot
            layer_tag = ""
    else:
        src_for_dot = filtered_dot
        layer_tag = ""

    # dot 実行時の追加属性（“縦寄せ”重視）
    extra_graph_attrs = [
        "-Grankdir=TB",
        "-Gnodesep=0.35",
        "-Granksep=0.80",
        "-Goverlap=false",
        "-Gsplines=true",
        "-Gconcentrate=true",
        "-Gratio=compress",
        "-Gmargin=0,0",
        "-Gpack=true",
        "-Gpackmode=graph",
    ]
    if FORCE_VIEWPORT:
        extra_graph_attrs.append(f"-Gviewport={FORCE_VIEWPORT}")

    def _run_dot(src_dot: Path):
        cmd = [dot_bin, "-Tsvg", *extra_graph_attrs, str(src_dot), "-o", str(SVG)]
        subprocess.run(cmd, check=True)

    try:
        _run_dot(src_for_dot)
        print(f"+ built {SVG} from {dot_file.name} (hide={'on' if HIDE_GRAVEYARD else 'off'}, "
              f"filter={used_backend}{layer_tag}{', viewport='+FORCE_VIEWPORT if FORCE_VIEWPORT else ''})")
    except subprocess.CalledProcessError as e:
        print(f"! dot failed: {e}")
        return False
    finally:
        for tmp in (src_for_dot, filtered_dot):
            if tmp is not dot_file:
                try: tmp.unlink(missing_ok=True)
                except Exception: pass

    # 健全性チェック → だめなら非フィルタ&フォールバック
    aspect = _svg_aspect(SVG)
    size_ok = SVG.exists() and SVG.stat().st_size >= 15_000
    aspect_ok = (aspect is not None and 0.2 <= aspect <= 8.0)
    nodes_ok = (not HIDE_GRAVEYARD) or (kept_nodes < 0 or kept_nodes >= 5)
    if not (size_ok and aspect_ok and nodes_ok):
        print(f"! degenerate svg (size_ok={size_ok}, aspect={aspect}, nodes_ok={nodes_ok}) → rebuild without filtering")
        tmp_src = dot_file
        try:
            cmd = ["dot", "-Tsvg",
                   "-Grankdir=TB","-Gnodesep=0.35","-Granksep=0.80",
                   "-Goverlap=false","-Gsplines=true","-Gconcentrate=true",
                   "-Gratio=compress","-Gmargin=0,0","-Gpack=true","-Gpackmode=graph",
                   str(tmp_src), "-o", str(SVG)]
            subprocess.run(cmd, check=True)
            print("+ rebuilt without filtering")
        except subprocess.CalledProcessError:
            sfdp = shutil.which("sfdp")
            if sfdp:
                try:
                    subprocess.run([sfdp, "-Tsvg", str(tmp_src), "-o", str(SVG)], check=True)
                    print("+ rebuilt via sfdp (fallback)")
                except subprocess.CalledProcessError:
                    pass
            twopi = shutil.which("twopi")
            if twopi:
                try:
                    subprocess.run([twopi, "-Tsvg", str(tmp_src), "-o", str(SVG)], check=True)
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

# ================== Context & static sync ==================
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

# ================== Main ==================
if __name__ == "__main__":
    ensure_context()
    build_svg_from_dot()
    svg_to_png()
    sync_to_static()
    if SVG.exists():
        print(f"i SVG updated at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(SVG.stat().st_mtime))}")
