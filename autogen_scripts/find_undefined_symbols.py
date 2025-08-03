import os
import re

FOLDER = "./generated_code"

# 除外するモジュール名・変数名のリスト
EXCLUDE_MODULES = {
    "pytest", "unittest", "patch", "numpy", "pandas", "talib",
    "os", "sys", "json", "datetime", "re", "subprocess", "logging",
    "asyncio", "uuid", "collections", "typing", "pathlib", "dotenv",
    "openai"
}

# 変数・定数名のように「モジュールでない可能性が高い名前」
EXCLUDE_SYMBOLS = {
    "DATA_SOURCE_URL", "LOCAL_DATA_PATH", "FEATURES_PATH", "MODEL_PATH",
    "MODEL_SAVE_PATH", "CONFIG_PATH", "LOG_FILE", "API_KEY",
}

results = []

def extract_imports(code):
    imports = []
    pattern_from = r'from\s+(\w+)\s+import\s+([\w, ]+)'
    for match in re.finditer(pattern_from, code):
        mod = match.group(1)
        symbols = [s.strip() for s in match.group(2).split(',')]
        imports.append((mod, symbols))
    pattern_import = r'import\s+(\w+)'
    for match in re.finditer(pattern_import, code):
        mod = match.group(1)
        imports.append((mod, []))
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
        # ① 除外モジュールなら無視
        if mod in EXCLUDE_MODULES:
            continue
        # ② 除外シンボル（モジュール名として誤認されてるもの）なら無視
        if mod in EXCLUDE_SYMBOLS:
            continue
        # ③ モジュールファイルがなければ警告
        if mod not in pyfiles:
            results.append(f"{fname}: モジュール '{mod}' が存在しません")
            continue
        # ④ シンボルがないかチェック
        if not symbols:
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
    with open(os.path.join(FOLDER, "undefined_symbols.txt"), "w", encoding="utf-8") as uf:
        uf.write("\n".join(results))
else:
    print("All test imports resolved!")
    with open(os.path.join(FOLDER, "undefined_symbols.txt"), "w", encoding="utf-8") as uf:
        uf.write("=== 0 missing ===\n")
