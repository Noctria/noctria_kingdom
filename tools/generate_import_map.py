# tools/generate_import_map.py

import os
import re
from collections import defaultdict

SRC_ROOT = "src"

def find_py_files(root):
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.endswith('.py'):
                yield os.path.join(dirpath, f)

def parse_imports(file_path):
    """
    そのファイルからimportしている「src配下の自作ファイル」だけ抽出
    """
    imports = set()
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # from src.xxxx import ...
            m1 = re.match(r'(from|import)\s+src\.([a-zA-Z0-9_\.]+)', line)
            if m1:
                mod = m1.group(2).replace('.', '/')
                imports.add(mod)
            # from core.xxxx import ... / import core.xxxx
            m2 = re.match(r'(from|import)\s+core\.([a-zA-Z0-9_\.]+)', line)
            if m2:
                mod = "core/" + m2.group(2).replace('.', '/')
                imports.add(mod)
            # from veritas.xxxx import ... / import veritas.xxxx
            m3 = re.match(r'(from|import)\s+veritas\.([a-zA-Z0-9_\.]+)', line)
            if m3:
                mod = "veritas/" + m3.group(2).replace('.', '/')
                imports.add(mod)
    return imports

# 1. 全ファイルmap作成
py_files = list(find_py_files(SRC_ROOT))
file_map = {os.path.splitext(os.path.relpath(f, SRC_ROOT))[0].replace("\\", "/"): f for f in py_files}
imports_map = defaultdict(set)
reverse_imports_map = defaultdict(set)

# 2. 各ファイル→import先 を登録
for f in py_files:
    key = os.path.splitext(os.path.relpath(f, SRC_ROOT))[0].replace("\\", "/")
    for dep in parse_imports(f):
        dep_path = os.path.join(SRC_ROOT, dep + ".py")
        if os.path.exists(dep_path):
            dep_key = os.path.splitext(os.path.relpath(dep_path, SRC_ROOT))[0].replace("\\", "/")
            imports_map[key].add(dep_key)
            reverse_imports_map[dep_key].add(key)

# 3. 孤立ファイル（どこからもimportされていないファイル＝reverse_imports_mapに登場しない）
isolated_files = [k for k in file_map if k not in reverse_imports_map and not k.endswith("__init__")]

# 4. Mermaidグラフ生成
lines = ["flowchart TD"]
for node, deps in imports_map.items():
    for dep in deps:
        n1 = node.replace("/", "_")
        n2 = dep.replace("/", "_")
        lines.append(f'    {n1}["{os.path.basename(node)}"] --> {n2}["{os.path.basename(dep)}"]')

# 孤立ノードに色（例: 赤色）をつけて追加
for node in isolated_files:
    n = node.replace("/", "_")
    lines.append(f'    {n}["{os.path.basename(node)} (孤立)"]:::isolated')
lines.append('classDef isolated fill:#faa,stroke:#f44,stroke-width:2px;')

# 5. Mermaidファイル出力
with open("kingdom_import_map.mmd", "w", encoding="utf-8") as f:
    f.write('\n'.join(lines))

print("---- 孤立ファイル一覧 ----")
for f in isolated_files:
    print(f"  - {file_map[f]}")
print("-----------------------")
print("Mermaid mmd generated: kingdom_import_map.mmd")
