import os
import re

FOLDER = "./generated_code"
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
    # クラスと関数定義
    for m in re.finditer(r'^class\s+(\w+)|^def\s+(\w+)', code, re.MULTILINE):
        defs.update([d for d in m.groups() if d])
    # 変数定義（シンプルに先頭の単語 = で抽出）
    for m in re.finditer(r'^(\w+)\s*=', code, re.MULTILINE):
        defs.add(m.group(1))
    return defs

# モジュールファイル一覧（テストファイルは除外）
pyfiles = {f[:-3]: f for f in os.listdir(FOLDER) if f.endswith(".py") and not f.startswith("test_")}

# テストファイルだけ抽出
test_files = [f for f in os.listdir(FOLDER) if f.startswith("test_") and f.endswith(".py")]

for fname in test_files:
    path = os.path.join(FOLDER, fname)
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    for mod, symbols in extract_imports(code):
        if mod not in pyfiles:
            results.append(f"{fname}: モジュール '{mod}' が存在しません")
            continue
        target_path = os.path.join(FOLDER, pyfiles[mod])
        with open(target_path, "r", encoding="utf-8") as tf:
            target_code = tf.read()
        defs = extract_defs(target_code)
        for sym in symbols:
            if sym not in defs:
                results.append(f"{fname}: '{sym}' not defined in {pyfiles[mod]}")

if results:
    print("=== Missing class/function/variable definitions ===")
    for line in results:
        print(line)
    # ファイルに出力
    with open(os.path.join(FOLDER, "undefined_symbols.txt"), "w", encoding="utf-8") as uf:
        uf.write("\n".join(results))
else:
    print("All test imports resolved!")
    # 空ファイルも更新
    with open(os.path.join(FOLDER, "undefined_symbols.txt"), "w", encoding="utf-8") as uf:
        uf.write("=== 0 missing ===\n")
