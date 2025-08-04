import os
import ast
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # ← adjust if needed
TARGET_DIRS = ["src", "noctria_gui", "tools", "scripts"]  # 走査したいディレクトリ名

# --- ファイル名からノードID生成 ---
def file_to_node(path):
    # ファイル名の拡張子・パス区切りを_に
    return str(path).replace("/", "_").replace(".", "_")

def relpath(p): return os.path.relpath(p, PROJECT_ROOT)

# --- 依存解析（import/static template依存） ---
def analyze_imports(filepath):
    imports = set()
    templates = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
        # テンプレートファイル呼び出し
        for line in src.splitlines():
            if "templates" in line and (".html" in line or ".jinja" in line):
                import re
                found = re.findall(r'["\']([\w/]+\.(?:html|jinja2?))["\']', line)
                templates.update(found)
    except Exception as e:
        print(f"[WARN] {filepath}: {e}")
    return imports, templates

# --- すべての.pyファイルとtemplateファイルを探索 ---
py_files = []
templates = set()
for dir in TARGET_DIRS:
    for root, _, files in os.walk(PROJECT_ROOT / dir):
        for f in files:
            if f.endswith(".py"):
                py_files.append(Path(root) / f)
            elif f.endswith((".html", ".jinja", ".jinja2")):
                templates.add(os.path.relpath(os.path.join(root, f), PROJECT_ROOT))

# --- 依存グラフ作成 ---
edges = []
node_files = set()
template_files = set(templates)
file2imports = defaultdict(set)
file2templates = defaultdict(set)

for py in py_files:
    imports, temp_deps = analyze_imports(py)
    node_files.add(relpath(py))
    file2imports[relpath(py)] = imports
    file2templates[relpath(py)] = temp_deps

# --- Pythonファイル間のimportエッジ作成 ---
for src in node_files:
    src_mod = Path(src).stem
    for dep in file2imports[src]:
        # 他のpythonファイルから該当モジュール名をもつファイルを探す
        for tgt in node_files:
            if Path(tgt).stem == dep and src != tgt:
                edges.append((src, tgt, "import"))
    for temp in file2templates[src]:
        if temp in template_files:
            edges.append((src, temp, "template"))

# --- すべてのノードの分類 ---
used_nodes = set()
for a, b, _ in edges:
    used_nodes.add(a)
    used_nodes.add(b)

isolated = []
non_isolated = []
for n in list(node_files) + list(template_files):
    if n not in used_nodes:
        isolated.append(n)
    else:
        non_isolated.append(n)

# --- Mermaid記法に出力 ---
def print_mmd(edges, isolated, non_isolated, show_templates=True):
    print("flowchart TD")
    # 通常エッジ
    for a, b, typ in edges:
        if typ == "import":
            print(f'    "{a}" --> "{b}"')
        elif typ == "template" and show_templates:
            print(f'    "{a}" -- template --> "{b}"')
    # 孤立ノード
    for n in isolated:
        print(f'    "{n}":::isolated')
    # スタイル
    print('    classDef isolated fill:#fff,stroke:#a00,stroke-width:2px;')

print("# ------ 非孤立ファイル/テンプレート ------")
print_mmd(edges, [], non_isolated)
print("\n# ------ 孤立ファイル ------")
print_mmd([], isolated, [])

