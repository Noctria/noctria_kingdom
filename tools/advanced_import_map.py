# tools/advanced_import_map.py
import ast
from pathlib import Path
from collections import defaultdict

def extract_imports(filepath):
    imports = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.add(n.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except Exception as e:
        print(f"⚠️ {filepath}: {e}")
    return imports

def main():
    base_dirs = ["src", "noctria_gui"]
    files = []
    for base in base_dirs:
        files += list(Path(base).rglob("*.py"))
    import_map = defaultdict(set)
    for f in files:
        mods = extract_imports(str(f))
        if mods:
            print(f"{f}: {mods}")   # ← 必ずprint
        for m in mods:
            import_map[str(f)].add(m)
    print("=== 合計ファイル数:", len(files))

if __name__ == "__main__":
    main()
