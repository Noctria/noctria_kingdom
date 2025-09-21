#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_context.py
  - imports.dot から依存グラフを読み、フォーカス近傍の編集許可リストを作る
  - codex_reports/context/allowed_files.txt と context_pack.json を更新

Usage:
  python scripts/build_context.py --focus noctria_gui/routes/pdca_api.py --radius 2
  python scripts/build_context.py --focus noctria_gui.routes.pdca_api --radius 2
"""

from __future__ import annotations
from pathlib import Path
import argparse, json, os, re, sys
from collections import deque, defaultdict

ROOT = Path(__file__).resolve().parents[1]
GRDIR = ROOT / "codex_reports" / "graphs"
CTXDIR = ROOT / "codex_reports" / "context"
DOT = GRDIR / "imports.dot"
CTX = CTXDIR / "context_pack.json"
ALLOWED = CTXDIR / "allowed_files.txt"

EDGE_RE = re.compile(r'(?P<a>"[^"]+"|[^\s\[\];]+)\s*->\s*(?P<b>"[^"]+"|[^\s\[\];]+)')


def _norm_node(s: str) -> str:
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s


def read_graph(dot_path: Path):
    adj = defaultdict(set)
    rev = defaultdict(set)
    nodes = set()
    txt = dot_path.read_text(encoding="utf-8", errors="ignore")
    for m in EDGE_RE.finditer(txt):
        a = _norm_node(m.group("a"))
        b = _norm_node(m.group("b"))
        if not a or not b:
            continue
        adj[a].add(b)
        rev[b].add(a)
        nodes.add(a)
        nodes.add(b)
    return nodes, adj, rev


def to_module_and_candidates(name_or_path: str):
    """
    入力がファイルパスでもモジュール名でも良い。
    返り値: (module_name, candidates_for_path_match [str, ...])
    """
    if name_or_path.endswith(".py"):
        rel = name_or_path.replace("\\", "/")
        if rel.startswith("./"):
            rel = rel[2:]
        mod = rel[:-3].replace("/", ".")
        base = rel
        return mod, [base, Path(rel).name, Path(rel).stem]
    else:
        mod = name_or_path.replace("/", ".")
        last = mod.split(".")[-1]
        return mod, [mod.replace(".", "/") + ".py", last + ".py", last]


def bfs_neighborhood(start: str, nodes, adj, rev, radius: int):
    if start not in nodes:
        # best-effort: 部分一致で拾う
        matches = [n for n in nodes if n.endswith(start) or n.endswith(start.replace("/", "."))]
        if matches:
            start = matches[0]
        else:
            return set([start])
    seen = {start}
    q = deque([(start, 0)])
    while q:
        u, d = q.popleft()
        if d == radius:
            continue
        for v in adj.get(u, ()):
            if v not in seen:
                seen.add(v)
                q.append((v, d + 1))
        for v in rev.get(u, ()):
            if v not in seen:
                seen.add(v)
                q.append((v, d + 1))
    return seen


def map_node_to_file(node: str, src_roots: list[Path]) -> list[Path]:
    """
    ノード名をそれっぽいファイルにマップする素朴法:
      - node を module っぽく扱い、/ にして .py を探す
      - プロジェクト内を軽く探索
    """
    cand = []
    # module → path 候補
    module_style = node.replace(".", "/")
    cand += [module_style + ".py", Path(module_style).name + ".py"]
    # 余計な prefix を削って再試行（e.g., package.__init__)
    if module_style.endswith("/__init__"):
        cand.append(module_style[:-9] + ".py")
    results: list[Path] = []
    for root in src_roots:
        for c in cand:
            p = root / c
            if p.exists():
                results.append(p)
    return results


def discover_src_roots() -> list[Path]:
    # よくあるレイアウトを候補に
    roots = [ROOT]
    for name in ("src", "app", "noctria_gui", "noctria_kernel"):
        p = ROOT / name
        if p.exists():
            roots.append(p)
    # 重複除去
    seen = set()
    out = []
    for r in roots:
        rp = r.resolve()
        if str(rp) in seen:
            continue
        seen.add(str(rp))
        out.append(rp)
    return out


def write_allowed(paths: list[Path]):
    CTXDIR.mkdir(parents=True, exist_ok=True)
    txt = "\n".join(str(p.relative_to(ROOT)).replace("\\", "/") for p in sorted(set(paths)))
    ALLOWED.write_text(txt + ("\n" if txt else ""), encoding="utf-8")
    print(f"+ wrote {ALLOWED.relative_to(ROOT)} ({len(paths)} files)")


def update_context_pack(focus: str, radius: int, files: list[Path], neighborhood: set[str]):
    CTXDIR.mkdir(parents=True, exist_ok=True)
    if CTX.exists():
        try:
            js = json.loads(CTX.read_text(encoding="utf-8"))
        except Exception:
            js = {}
    else:
        js = {}
    js.setdefault("version", 1)
    js["focus"] = focus
    js["radius"] = radius
    js["allowlist_files"] = [
        str(p.relative_to(ROOT)).replace("\\", "/") for p in sorted(set(files))
    ]
    js.setdefault("meta", {})["neighborhood"] = sorted(neighborhood)
    CTX.write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"+ updated {CTX.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--focus", required=True, help="モジュール名 or ファイルパス")
    ap.add_argument("--radius", type=int, default=2, help="近傍半径（上下流合計）")
    ap.add_argument("--dot", default=str(DOT), help="imports.dot パス")
    args = ap.parse_args()

    dotp = Path(args.dot)
    if not dotp.exists():
        print(f"ERR: DOT not found: {dotp}", file=sys.stderr)
        sys.exit(1)

    nodes, adj, rev = read_graph(dotp)
    mod, _ = to_module_and_candidates(args.focus)

    neighborhood = bfs_neighborhood(mod, nodes, adj, rev, args.radius)
    if not neighborhood:
        neighborhood = {mod}

    # ノード→ファイル解決
    src_roots = discover_src_roots()
    files: list[Path] = []
    for n in neighborhood:
        files += map_node_to_file(n, src_roots)
    # ダブり除去
    uniq = []
    seen = set()
    for p in files:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)

    write_allowed(uniq)
    update_context_pack(args.focus, args.radius, uniq, neighborhood)


if __name__ == "__main__":
    main()
