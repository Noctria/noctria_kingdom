import os, re, sys, csv, json, hashlib, pathlib
ROOT = pathlib.Path(".").resolve()
OUT  = ROOT/"codex_reports"/"graphs"
OUT.mkdir(parents=True, exist_ok=True)

# ====== 設定 ======
INCLUDE = ["src", "noctria_gui", "airflow_docker/dags", "_graveyard"]  # 必要に応じ編集
EXCLUDE = {
    ".git", "venv_noctria", ".mypy_cache", ".pytest_cache", "__pycache__",
    "node_modules", ".idea", ".vscode", "codex_reports/graphs"
}
MERMAID_PAGE_MAX_NODES = 800
MERMAID_PAGE_MAX_EDGES = 2000

# ====== 共通 ======
def is_excluded(p: pathlib.Path)->bool:
    try:
        rel = p.relative_to(ROOT)
    except ValueError:
        return True
    parts = rel.parts
    if not parts:
        return True
    for i in range(len(parts)):
        sub = "/".join(parts[:i+1])
        if sub in EXCLUDE or parts[i] in EXCLUDE:
            return True
    return False

def sha1(path: pathlib.Path)->str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def iter_paths():
    tops = [ROOT/t for t in INCLUDE if (ROOT/t).exists()]
    for top in tops:
        for p in top.rglob("*"):
            if is_excluded(p):
                continue
            yield p

# ====== 1) manifest ======
manifest_rows = []
for p in iter_paths():
    rel = p.relative_to(ROOT).as_posix()
    t = "dir" if p.is_dir() else "file"
    size = (p.stat().st_size if p.is_file() else 0)
    gflag = rel.startswith("_graveyard/")
    sha = (sha1(p) if p.is_file() else "")
    manifest_rows.append({"path": rel, "type": t, "size": size, "sha1": sha, "quarantined": int(gflag)})

with open(OUT/"manifest.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["path","type","size","sha1","quarantined"])
    w.writeheader(); w.writerows(manifest_rows)

with open(OUT/"manifest.jsonl","w",encoding="utf-8") as f:
    for r in manifest_rows:
        f.write(json.dumps(r, ensure_ascii=False)+"\n")

# ====== 2) ファイル階層 DOT ======
nodes = {}  # rel -> nid
edges = []  # (parent_rel, child_rel)

def add_node(rel):
    if rel not in nodes:
        nodes[rel] = f"n{len(nodes)+1}"

def parent_of(rel):
    if "/" in rel:
        return rel.rsplit("/",1)[0]
    return ""

paths_sorted = sorted([r["path"] for r in manifest_rows], key=lambda s:(s.count("/"), s))
for rel in paths_sorted:
    add_node(rel)
    par = parent_of(rel)
    if par:
        add_node(par); edges.append((par, rel))

dot_lines = []
dot_lines.append('digraph files_tree {')
dot_lines.append('  graph [rankdir=LR, fontsize=10]; node [shape=box, fontsize=9]; edge [arrowhead=none, color="#aaaaaa"];')

tops = {}
for rel in nodes.keys():
    top = rel.split("/",1)[0]
    tops.setdefault(top, []).append(rel)

for i,(top, members) in enumerate(sorted(tops.items())):
    dot_lines.append(f'  subgraph cluster_{i} {{ label="{top}"; fontsize=12; style=rounded; color="#cccccc";')
    file_set = {r["path"] for r in manifest_rows if r["type"]=="file"}
    dir_set  = {r["path"] for r in manifest_rows if r["type"]=="dir"}
    for m in sorted(members):
        nid = nodes[m]
        label = m
        looks_like_dir = any(x.startswith(m+"/") for x in file_set) or m in dir_set
        shape = "folder" if looks_like_dir else "note"
        color = "#cfe8ff" if m.startswith("_graveyard/") else "#ffffff"
        dot_lines.append(f'    {nid} [label="{label}", shape=box, style="filled,rounded", fillcolor="{color}"];')
    dot_lines.append("  }")

for a,b in edges:
    dot_lines.append(f'  {nodes[a]} -> {nodes[b]};')

dot_lines.append("}")
(OUT/"files_tree.dot").write_text("\n".join(dot_lines), encoding="utf-8")

# ====== 3) Python import 依存 DOT ======
PY_RE = re.compile(r'^\s*(?:from\s+([A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z0-9_\.]+))', re.M)
def to_module(p: pathlib.Path):
    for t in INCLUDE:
        base = ROOT/t
        if base.exists():
            try:
                rel = p.relative_to(base).with_suffix("")
                return (t.replace("/",".")) + "." + ".".join(rel.parts)
            except ValueError:
                continue
    return None

mods = set(); edges_imp = set()
for p in iter_paths():
    if p.suffix != ".py" or not p.is_file(): continue
    mod = to_module(p)
    if not mod: continue
    mods.add(mod)
    txt = p.read_text(encoding="utf-8", errors="ignore")
    for m in PY_RE.finditer(txt):
        tgt = m.group(1) or m.group(2)
        if not tgt: continue
        if any(tgt.startswith(x.replace("/",".")) for x in INCLUDE):
            edges_imp.add((mod, tgt))

mods = sorted(mods)
mod_id = {m:f"m{idx+1}" for idx,m in enumerate(mods)}
dot2 = []
dot2.append('digraph imports {')
dot2.append('  graph [overlap=false, splines=true, fontsize=10]; node [shape=box, fontsize=9]; edge [color="#888888"];')

tops2 = {}
for m in mods:
    top = m.split(".",1)[0]
    tops2.setdefault(top, []).append(m)

for i,(top, members) in enumerate(sorted(tops2.items())):
    dot2.append(f'  subgraph cluster_imp_{i} {{ label="{top}"; fontsize=12; style=rounded; color="#cccccc";')
    for m in sorted(members):
        color = "#ffe0e0" if m.startswith("_graveyard.") else "#ffffff"
        dot2.append(f'    {mod_id[m]} [label="{m}", style=filled, fillcolor="{color}"];')
    dot2.append("  }")

for a,b in sorted(edges_imp):
    if a in mod_id and b in mod_id:
        dot2.append(f'  {mod_id[a]} -> {mod_id[b]};')

dot2.append("}")
(OUT/"imports.dot").write_text("\n".join(dot2), encoding="utf-8")

# ====== 4) 分割Mermaid ======
all_nodes = list(nodes.keys())
all_edges = edges[:]
pages = []
curN, curE = [], []
for rel in all_nodes:
    if len(curN) >= MERMAID_PAGE_MAX_NODES:
        pages.append((curN, curE)); curN, curE = [], []
    curN.append(rel)
pages.append((curN, curE))
for idx,(ns, es) in enumerate(pages):
    ns_set = set(ns)
    es2 = [e for e in all_edges if e[0] in ns_set and e[1] in ns_set][:MERMAID_PAGE_MAX_EDGES]
    pages[idx] = (ns, es2)

PAGEDIR = OUT/"pages"; PAGEDIR.mkdir(exist_ok=True, parents=True)
for i,(ns,es) in enumerate(pages, start=1):
    lines = ["flowchart TD"]
    for n in ns:
        nid = "N_" + n.replace("/","_").replace(".","_")
        lines.append(f'  {nid}["{n}"]')
    for a,b in es:
        aid = "N_" + a.replace("/","_").replace(".","_")
        bid = "N_" + b.replace("/","_").replace(".","_")
        lines.append(f"  {aid} --- {bid}")
    (PAGEDIR/f"page_{i:03d}.mmd").write_text("\n".join(lines), encoding="utf-8")

print("[OK] manifest:", (OUT/'manifest.csv'))
print("[OK] files_tree.dot:", (OUT/'files_tree.dot'))
print("[OK] imports.dot:", (OUT/'imports.dot'))
print("[OK] mermaid pages:", (PAGEDIR))

