#!/usr/bin/env python3
# coding: utf-8
"""
Repository scanner → Mermaid (.mmd) generator
- ルート配下のファイルを再帰走査し、中身を"全文"読み込んで依存関係と用途を推定。
- PythonはASTで import / from を解析し、可能ならローカルファイルに解決。
- Dockerfileの COPY/ADD、docker-compose の volumes/env_file/depends_on 等を検出。
- requirements*.txt は外部依存としてノード化。
- Mermaidにサブグラフ（トップレベルディレクトリ単位）とノード種別スタイルを出力。

使い方:
  python tools/scan_repo_to_mermaid.py \
    --root /mnt/d/noctria_kingdom \
    --output /mnt/d/noctria_kingdom/data/repo_dependencies.mmd

主な引数:
  --root        走査開始ディレクトリ（必須）
  --output      出力 .mmd パス（未指定なら stdout）
  --exclude     追加除外パターン（複数可, glob）例: --exclude 'data/**' --exclude '*.ipynb'
  --follow-symlinks  シンボリックリンク辿る（既定は辿らない）
"""

from __future__ import annotations
import argparse
import ast
import fnmatch
import io
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# --------- 検出/分類のヘルパ ---------

TEXT_LIKE_EXT = {
    ".py", ".pyi", ".pyx",
    ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf", ".env",
    ".md", ".mmd", ".txt", ".csv", ".tsv",
    ".dockerfile", ".dockerignore",
    ".sh", ".bash", ".zsh",
    ".sql",
    ".cfg", ".properties",
    ".rst",
    ".jinja", ".j2",
    ".xml",
    ".gitignore", ".gitattributes",
    ".tf", ".tfvars",
    ".service",
    ".log",  # ログも読みたいなら
}
BINARY_LIKE_EXT = {
    ".zip", ".gz", ".bz2", ".xz", ".7z",
    ".png", ".jpg", ".jpeg", ".webp", ".ico",
    ".pdf", ".pptx", ".docx", ".xlsx",
    ".whl", ".so", ".dylib", ".dll", ".bin",
}

DEFAULT_EXCLUDES = [
    ".git/**",
    "**/__pycache__/**",
    "node_modules/**",
    "venv/**",
    ".venv/**",
    "logs/**",
    "airflow_docker/logs/**",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.pyd",
    "**/.mypy_cache/**",
    "**/.pytest_cache/**",
    ".idea/**", ".vscode/**",
]

ROLE_STYLES = {
    "python": "py",
    "airflow_dag": "dag",
    "dockerfile": "docker",
    "compose": "yaml",
    "yaml": "yaml",
    "requirements": "req",
    "shell": "sh",
    "config": "cfg",
    "docs": "docs",
    "env": "env",
    "other": "other",
    "dir": "dir",
    "external": "ext",
}

def guess_role(path: Path, content: str) -> str:
    p = path
    name = p.name.lower()
    suffix = p.suffix.lower()

    if p.is_dir():
        return "dir"
    if suffix == ".py":
        # Airflow DAG らしさ
        if "from airflow" in content or "DAG(" in content:
            return "airflow_dag"
        return "python"
    if name in {"dockerfile"} or suffix == ".dockerfile":
        return "dockerfile"
    if name in {"docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml"}:
        return "compose"
    if suffix in {".yml", ".yaml"}:
        return "yaml"
    if name.startswith("requirements") and suffix == ".txt":
        return "requirements"
    if suffix in {".sh", ".bash", ".zsh"}:
        return "shell"
    if suffix in {".md", ".mmd", ".rst"}:
        return "docs"
    if name in {".env", } or suffix in {".env"}:
        return "env"
    if suffix in {".ini", ".cfg", ".conf", ".toml", ".json"}:
        return "config"
    return "other"

# --------- Python import 解析（AST） ---------

class PyImports(ast.NodeVisitor):
    def __init__(self):
        self.imports: Set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name:
                self.imports.add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # node.module may be None (relative import like from . import x)
        mod = node.module or ""
        level = getattr(node, "level", 0) or 0
        if level > 0:
            # 相対importは "._"*level + module という表現にしておく（後で解決）
            dot = "." * level
            base = f"{dot}{mod}" if mod else dot
            self.imports.add(base)
        else:
            if mod:
                self.imports.add(mod)

def build_python_module_index(root: Path) -> Dict[str, Path]:
    """
    ルート配下の .py を "ドット表記モジュール" にマップする。
    パッケージの有無に関わらず、ディレクトリ→ドット変換で広めに対応。
    """
    idx: Dict[str, Path] = {}
    for p in root.rglob("*.py"):
        if p.is_symlink():
            continue
        rel = p.relative_to(root)
        # 例: src/plan_data/feature_spec.py -> src.plan_data.feature_spec
        mod = ".".join(rel.with_suffix("").parts)
        idx[mod] = p
    return idx

def resolve_relative_module(current_mod: str, rel: str) -> Optional[str]:
    """
    current_mod: 例 'src.plan_data.observation_adapter'
    rel: '.feature_spec' / '..utils' / '...'
    """
    if not rel.startswith("."):
        return rel
    level = len(rel) - len(rel.lstrip("."))
    tail = rel.lstrip(".")
    parts = current_mod.split(".")
    if len(parts) < level:
        return None
    base = parts[: len(parts) - level]
    if tail:
        base += tail.split(".")
    if not base:
        return None
    return ".".join(base)

# --------- 依存関係抽出 ---------

EDGE = Tuple[str, str]  # (src_id, dst_id)

def sanitize_id(s: str) -> str:
    # MermaidのノードID用に安全化
    return re.sub(r"[^A-Za-z0-9_]", "_", s)

def read_text_full(p: Path) -> str:
    # テキストとして全読込み（バイナリは除外）
    try:
        with p.open("rb") as f:
            raw = f.read()
        # 可能性: utf-8 / cp932 / latin-1 の順にトライ
        for enc in ("utf-8", "cp932", "latin-1"):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def should_exclude(path: Path, excludes: List[str], root: Path) -> bool:
    rel = str(path.relative_to(root))
    for pat in excludes:
        if fnmatch.fnmatch(rel, pat):
            return True
    return False

def parse_dockerfile_refs(content: str) -> Set[str]:
    refs: Set[str] = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # COPY/ADD src... dest
        m = re.match(r"^(COPY|ADD)\s+(.+?)\s+(.+)$", line, re.IGNORECASE)
        if m:
            srcs = m.group(2)
            # 複数ソース: 空白区切り or ["a", "b"]
            if srcs.startswith("["):
                for s in re.findall(r'"([^"]+)"', srcs):
                    refs.add(s)
            else:
                for s in srcs.split():
                    refs.add(s)
    return refs

def parse_compose_refs(content: str) -> Set[str]:
    refs: Set[str] = set()
    # volumes: "./src:/opt/airflow/src" / "./dags:..."
    for m in re.finditer(r"volumes:\s*((?:\n\s*-\s*.+)+)", content, re.IGNORECASE):
        block = m.group(1)
        for v in re.findall(r"-\s*([^\n#]+)", block):
            host = v.split(":")[0].strip().strip('"').strip("'")
            if host and (host.startswith("./") or host.startswith("../") or host == "."):
                refs.add(host)
    # env_file:
    for m in re.finditer(r"env_file:\s*((?:\n\s*-\s*.+)+|\s*[^\n]+)", content, re.IGNORECASE):
        block = m.group(1)
        for e in re.findall(r"-\s*([^\n#]+)", block) or [block]:
            e = e.strip()
            e = e.strip('"').strip("'")
            if e:
                refs.add(e)
    # dockerfile:
    for m in re.finditer(r"dockerfile:\s*([^\n#]+)", content, re.IGNORECASE):
        refs.add(m.group(1).strip())
    # build.context:
    for m in re.finditer(r"context:\s*([^\n#]+)", content, re.IGNORECASE):
        ctx = m.group(1).strip()
        if ctx:
            refs.add(ctx)
    return refs

def parse_requirements(content: str) -> Set[str]:
    pkgs: Set[str] = set()
    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("-r "):
            continue
        # 例 "pandas==2.2.2", "gymnasium>=0.29"
        name = re.split(r"[<>=!~\[\];\s]", s, maxsplit=1)[0]
        if name:
            pkgs.add(name)
    return pkgs

# --------- スキャン本体 ---------

def scan_repo(root: Path, excludes: List[str], follow_symlinks: bool) -> Tuple[
    Dict[str, Dict], List[EDGE], Dict[str, Set[str]]
]:
    """
    Returns:
      nodes: id -> {path, label, role}
      edges: (src_id, dst_id) list
      clusters: topdir -> set(node_ids)
    """
    nodes: Dict[str, Dict] = {}
    edges: List[EDGE] = []
    clusters: Dict[str, Set[str]] = {}

    # Pythonモジュール索引を先に作る
    py_index = build_python_module_index(root)

    # ファイル列挙
    paths: List[Path] = []
    for p in root.rglob("*"):
        if not follow_symlinks and p.is_symlink():
            continue
        if p.is_dir():
            # ディレクトリもノードにする（サブグラフに入れるため）
            if should_exclude(p, excludes, root):
                continue
            node_id = sanitize_id(str(p.relative_to(root)) + "/")
            nodes.setdefault(node_id, {
                "path": str(p.relative_to(root)) + "/",
                "label": f"{p.name}/",
                "role": "dir",
            })
            top = p.relative_to(root).parts[0] if p != root and len(p.relative_to(root).parts) > 0 else ""
            if top:
                clusters.setdefault(top, set()).add(node_id)
            continue

        if should_exclude(p, excludes, root):
            continue
        if p.suffix.lower() in BINARY_LIKE_EXT:
            continue  # バイナリは解析対象外（ノード化も省略）

        paths.append(p)

    # コンテンツ読み込み & 役割決定 & 依存抽出
    for p in paths:
        rel = p.relative_to(root)
        content = read_text_full(p)
        role = guess_role(p, content)
        node_id = sanitize_id(str(rel))
        label = p.name
        nodes[node_id] = {"path": str(rel), "label": label, "role": role}

        # クラスタ（トップレベルディレクトリ）
        parts = rel.parts
        if len(parts) >= 1:
            top = parts[0]
            clusters.setdefault(top, set()).add(node_id)

        # 依存解析
        if role in {"python", "airflow_dag"}:
            # Python import解析
            imports = set()
            try:
                imports = PyImports().visit(ast.parse(content)) or set()  # type: ignore
            except Exception:
                # AST失敗時は簡易正規表現フォールバック
                for m in re.finditer(r"^\s*import\s+([A-Za-z0-9_\.]+)", content, re.MULTILINE):
                    imports.add(m.group(1))
                for m in re.finditer(r"^\s*from\s+([\.A-Za-z0-9_]+)\s+import\s+", content, re.MULTILINE):
                    imports.add(m.group(1))

            # 自モジュール名（相対import解決用）
            my_mod = ".".join(rel.with_suffix("").parts)

            resolved: Set[str] = set()
            for imp in list(imports):
                if imp.startswith("."):
                    abs_mod = resolve_relative_module(my_mod, imp)
                    if abs_mod:
                        resolved.add(abs_mod)
                else:
                    resolved.add(imp)

            # ローカル解決
            for mod in resolved:
                # 完全一致で探す
                target = py_index.get(mod)
                if not target:
                    # モジュール名先頭だけ一致（import src.plan_data など）
                    for k, v in py_index.items():
                        if k == mod or k.startswith(mod + "."):
                            target = v
                            break
                if target:
                    dst_id = sanitize_id(str(target.relative_to(root)))
                    edges.append((node_id, dst_id))
                else:
                    # 外部依存としてノード化
                    ext_id = sanitize_id(f"ext::{mod.split('.')[0]}")
                    if ext_id not in nodes:
                        nodes[ext_id] = {"path": mod.split('.')[0], "label": mod.split('.')[0], "role": "external"}
                    edges.append((node_id, ext_id))

        elif role == "dockerfile":
            refs = parse_dockerfile_refs(content)
            for ref in refs:
                # 相対パスのみ対象
                ref_path = (p.parent / ref).resolve()
                if root in ref_path.parents or ref_path == root:
                    try:
                        rel_ref = ref_path.relative_to(root)
                    except Exception:
                        continue
                    dst_id = sanitize_id(str(rel_ref))
                    # 参照先がファイルで未登録なら仮ノード（役割はother）
                    if dst_id not in nodes:
                        nodes[dst_id] = {"path": str(rel_ref), "label": rel_ref.name, "role": "other"}
                    edges.append((node_id, dst_id))

        elif role == "compose":
            refs = parse_compose_refs(content)
            for ref in refs:
                ref_path = (p.parent / ref).resolve()
                if ref_path.exists():
                    try:
                        rel_ref = ref_path.relative_to(root)
                    except Exception:
                        continue
                    dst_id = sanitize_id(str(rel_ref))
                    if dst_id not in nodes:
                        # ディレクトリ参照の可能性あり
                        if ref_path.is_dir():
                            nodes[dst_id] = {"path": str(rel_ref) + "/", "label": rel_ref.name + "/", "role": "dir"}
                        else:
                            nodes[dst_id] = {"path": str(rel_ref), "label": rel_ref.name, "role": guess_role(ref_path, read_text_full(ref_path))}
                    edges.append((node_id, dst_id))
                else:
                    # 外部/未解決参照
                    ext_id = sanitize_id(f"ext::{ref}")
                    if ext_id not in nodes:
                        nodes[ext_id] = {"path": ref, "label": ref, "role": "external"}
                    edges.append((node_id, ext_id))

        elif role == "requirements":
            pkgs = parse_requirements(content)
            for pkg in pkgs:
                ext_id = sanitize_id(f"ext::{pkg}")
                if ext_id not in nodes:
                    nodes[ext_id] = {"path": pkg, "label": pkg, "role": "external"}
                edges.append((node_id, ext_id))

        else:
            # そのほかのファイルからの参照はここでは扱わないが、
            # 必要なら "source filename" や "python script.py" なども拾える
            pass

    return nodes, edges, clusters

# --------- Mermaid 生成 ---------

def render_mermaid(nodes: Dict[str, Dict], edges: List[EDGE], clusters: Dict[str, Set[str]]) -> str:
    out: List[str] = []
    out.append("%% auto-generated by scan_repo_to_mermaid.py")
    out.append("graph TD")
    out.append("  %% ノードスタイル定義")
    out.append('  classDef py fill:#E3F2FD,stroke:#1E88E5,stroke-width:1px;')
    out.append('  classDef dag fill:#FFF3E0,stroke:#FB8C00,stroke-width:1px;')
    out.append('  classDef yaml fill:#EDE7F6,stroke:#5E35B1,stroke-width:1px;')
    out.append('  classDef docker fill:#E8F5E9,stroke:#2E7D32,stroke-width:1px;')
    out.append('  classDef req fill:#F1F8E9,stroke:#7CB342,stroke-width:1px;')
    out.append('  classDef sh fill:#FBE9E7,stroke:#D84315,stroke-width:1px;')
    out.append('  classDef cfg fill:#ECEFF1,stroke:#546E7A,stroke-width:1px;')
    out.append('  classDef docs fill:#FFFDE7,stroke:#F9A825,stroke-width:1px;')
    out.append('  classDef env fill:#FFF8E1,stroke:#FBC02D,stroke-width:1px;')
    out.append('  classDef ext fill:#FCE4EC,stroke:#AD1457,stroke-width:1px;')
    out.append('  classDef dir fill:#EEEEEE,stroke:#616161,stroke-width:1px;')
    out.append('  classDef other fill:#FAFAFA,stroke:#9E9E9E,stroke-width:1px;')

    # サブグラフ（トップレベルディレクトリ）
    # ルート直下にないノード（extなど）はサブグラフ外に出す
    printed: Set[str] = set()

    for top, node_ids in clusters.items():
        if top == "" or top.startswith("."):
            continue
        out.append(f"  subgraph {top}")
        for nid in sorted(node_ids):
            n = nodes[nid]
            label = n["label"]
            role = n["role"]
            # Mermaid ノード: id["label"]:::class
            out.append(f'    {nid}["{label}"]:::{ROLE_STYLES.get(role, "other")}')
            printed.add(nid)
        out.append("  end")

    # サブグラフ外のノード
    for nid, n in nodes.items():
        if nid in printed:
            continue
        label = n["label"]
        role = n["role"]
        out.append(f'  {nid}["{label}"]:::{ROLE_STYLES.get(role, "other")}')

    # エッジ
    for src, dst in edges:
        if src not in nodes or dst not in nodes:
            continue
        out.append(f"  {src} --> {dst}")

    # ちょいLegend
    out.append("  %% Legend")
    out.append('  subgraph _Legend')
    for role, cls in ROLE_STYLES.items():
        if role in {"dir"}:
            continue
        nid = f"legend_{cls}"
        out.append(f'    {nid}["{role}"]:::{cls}')
    out.append("  end")

    return "\n".join(out)

# --------- CLI ---------

def main():
    ap = argparse.ArgumentParser(description="Scan repository and emit Mermaid (.mmd)")
    ap.add_argument("--root", required=True, help="root directory to scan")
    ap.add_argument("--output", help="output .mmd file path (default: stdout)")
    ap.add_argument("--exclude", action="append", default=[], help="extra exclude glob (can be repeated)")
    ap.add_argument("--follow-symlinks", action="store_true", help="follow symlinks")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] root not found: {root}", file=sys.stderr)
        sys.exit(2)

    excludes = DEFAULT_EXCLUDES + args.exclude

    nodes, edges, clusters = scan_repo(root, excludes=excludes, follow_symlinks=args.follow_symlinks)
    mmd = render_mermaid(nodes, edges, clusters)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(mmd, encoding="utf-8")
        print(f"[OK] Mermaid written to: {args.output} (nodes={len(nodes)}, edges={len(edges)})")
    else:
        print(mmd)

if __name__ == "__main__":
    main()
