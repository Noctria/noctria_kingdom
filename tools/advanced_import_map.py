from pathlib import Path
from collections import defaultdict
import ast

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
        pass
    return imports

def mod_name_from_path(p):
    # 例: src/strategies/aurus_singularis.py → strategies.aurus_singularis
    parts = Path(p).with_suffix('').parts
    if parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts)

def path_from_mod_name(mod_name, file_map):
    # 例: strategies.aurus_singularis → src/strategies/aurus_singularis.py
    for path, mod in file_map.items():
        if mod == mod_name:
            return path
    return None

def main():
    base_dirs = ["src", "noctria_gui"]
    files = []
    for base in base_dirs:
        files += list(Path(base).rglob("*.py"))
    file_mod_map = {str(f): mod_name_from_path(str(f)) for f in files}
    mod_file_map = {v: k for k, v in file_mod_map.items()}

    # ファイル→import先ファイル（.py存在ベースで）
    import_graph = defaultdict(set)
    for f in files:
        imps = extract_imports(str(f))
        for imp in imps:
            # .pyとして存在するimportのみ
            imp_py = path_from_mod_name(imp, file_mod_map)
            if imp_py:
                import_graph[str(f)].add(imp_py)

    # 誰からもimportされていない.py
    imported = set()
    for imps in import_graph.values():
        imported |= imps
    all_files = set(str(f) for f in files)
    isolated = all_files - imported

    print("# ------ 孤立ファイル (importされてない.py) ------")
    for f in sorted(isolated):
        print(f)

    print("\n# ------ Mermaid矢印（.py存在のみ） ------")
    print("flowchart TD")
    for f, imps in import_graph.items():
        for t in imps:
            print(f'    "{f}" --> "{t}"')

if __name__ == "__main__":
    main()
