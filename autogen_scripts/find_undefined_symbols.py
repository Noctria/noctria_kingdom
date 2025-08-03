import os
import re

FOLDER = "./generated_code"
results = []

def extract_imports(code):
    # from xxx import YYY, ZZZ パターン
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
    return defs

# 検索対象
pyfiles = {f[:-3]: f for f in os.listdir(FOLDER) if f.endswith(".py")}

for fname in os.listdir(FOLDER):
    if not fname.startswith("test_") or not fname.endswith(".py"):
        continue
    path = os.path.join(FOLDER, fname)
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    for mod, symbols in extract_imports(code):
        if mod in pyfiles:
            target_path = os.path.join(FOLDER, pyfiles[mod])
            with open(target_path, "r", encoding="utf-8") as tf:
                target_code = tf.read()
            defs = extract_defs(target_code)
            for sym in symbols:
                if sym not in defs:
                    results.append(f"{fname}: '{sym}' not defined in {pyfiles[mod]}")

if results:
    print("=== Missing class/function definitions ===")
    for line in results:
        print(line)
else:
    print("All test imports resolved!")
