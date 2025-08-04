# tools/advanced_import_map.py
import ast
from pathlib import Path
from collections import defaultdict

def extract_imports(filepath):
    imports = set()
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except Exception:
            return set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.add(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports

def main():
    base_dirs = ["src", "noctria_gui"]
    files = []
    for base in base_dirs:
        files += list(Path(base).rglob("*.py"))
    import_map = defaultdict(set)
    for f in files:
        mods = extract_imports(str(f))
        for m in mods:
            import_map[str(f)].add(m)
    # ここで「孤立」かどうかを判定（双方向性・テンプレート参照は別途）
    # ... 出力処理（Mermaid等）
