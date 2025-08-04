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
        # print(f"⚠️ {filepath}: {e}")
        pass
    return imports

def main():
    base_dirs = ["src", "noctria_gui"]
    files = []
    for base in base_dirs:
        files += list(Path(base).rglob("*.py"))

    # import_map: ファイル→import先
    import_map = defaultdict(set)
    # reverse_map: ファイル名→import元（誰にimportされてるか）
    reverse_map = defaultdict(set)

    # 拡張: ファイル名を"モジュールパス"形式にする
    path_to_mod = lambda p: str(p).replace("/", ".").replace("\\", ".").rstrip(".py")

    mod_name_map = {}
    for f in files:
        mods = extract_imports(str(f))
        mod_name = path_to_mod(f)
        mod_name_map[mod_name] = str(f)
        for m in mods:
            import_map[str(f)].add(m)

    # 逆参照マップ
    for f, imps in import_map.items():
        for m in imps:
            reverse_map[m].add(f)

    # 孤立ファイル: どこもimportせず、誰からもimportされていない
    all_files = set(str(f) for f in files)
    import_targets = set()
    for imps in import_map.values():
        import_targets.update(imps)

    non_isolated = set()
    for f, imps in import_map.items():
        if imps:
            non_isolated.add(f)
        # 逆参照されているなら非孤立
        mod_name = path_to_mod(f)
        if mod_name in reverse_map and reverse_map[mod_name]:
            non_isolated.add(f)

    isolated = all_files - non_isolated

    print("\n# ------ 非孤立ファイル ------")
    for f in sorted(non_isolated):
        print(f)

    print("\n# ------ 孤立ファイル ------")
    for f in sorted(isolated):
        print(f)

    # Mermaid出力例
    print("\nflowchart TD")
    for f, imps in import_map.items():
        for m in imps:
            print(f'    "{f}" --> "{m}"')

if __name__ == "__main__":
    main()
