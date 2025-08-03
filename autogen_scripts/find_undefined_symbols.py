import os
import re

FOLDER = "./generated_code"

def to_snake_case(name: str) -> str:
    # PascalCaseやCamelCaseをsnake_caseに変換（単純版）
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    snake = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    return snake

results = []

def extract_imports(code):
    pattern = r'from\s+(\w+)\s+import\s+([\w, ]+)'
    imports = []
    for match in re.finditer(pattern, code):
        mod = match.group(1)
        symbols = [s.strip() for s in match.group(2).split(',')]
        imports.append((mod, symbols))
    return imports

def extract_defs(code):
    defs = set()
    for m in re.finditer(r'^class\s+(\w+)|^def\s+(\w+)', code, re.MULTILINE):
        defs.update([d for d in m.groups() if d])
    for m in re.finditer(r'^(\w+)\s*=', code, re.MULTILINE):
        defs.add(m.group(1))
    return defs

pyfiles = {f[:-3]: f for f in os.listdir(FOLDER) if f.endswith(".py") and not f.startswith("test_")}

test_files = [f for f in os.listdir(FOLDER) if f.startswith("test_") and f.endswith(".py")]

for fname in test_files:
    path = os.path.join(FOLDER, fname)
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    for mod, symbols in extract_imports(code):
        # モジュール名をsnake_case化してファイルを探す
        mod_snake = to_snake_case(mod)
        if mod_snake not in pyfiles:
            results.append(f"{fname}: モジュール '{mod}' が存在しません (変換後: '{mod_snake}')")
            continue
        target_path = os.path.join(FOLDER, pyfiles[mod_snake])
        with open(target_path, "r", encoding="utf-8") as tf:
            target_code = tf.read()
        defs = extract_defs(target_code)
        for sym in symbols:
            if sym not in defs:
                results.append(f"{fname}: '{sym}' not defined in {pyfiles[mod_snake]}")

if results:
    print("=== Missing class/function/variable definitions ===")
    for line in results:
        print(line)
    with open(os.path.join(FOLDER, "undefined_symbols.txt"), "w", encoding="utf-8") as uf:
        uf.write("\n".join(results))
else:
    print("All test imports resolved!")
    with open(os.path.join(FOLDER, "undefined_symbols.txt"), "w", encoding="utf-8") as uf:
        uf.write("=== 0 missing ===\n")
