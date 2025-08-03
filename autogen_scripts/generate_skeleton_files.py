import os
import re

FOLDER = "./generated_code"
UNDEF_FILE = "./autogen_scripts/undefined_symbols.txt"

def add_skeleton_to_file(file_path, symbol):
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# 自動生成骨格ファイル\n\n")

    with open(file_path, "r+", encoding="utf-8") as f:
        content = f.read()
        # 既に骨格ありならスキップ
        if f"class {symbol}" in content or f"def {symbol}" in content or re.search(rf"\b{symbol}\b", content):
            return

        f.seek(0, os.SEEK_END)
        if symbol.isupper():
            # 定数の想定
            f.write(f"{symbol} = 'TODO:値'\n\n")
        elif symbol[0].isupper():
            # クラスの想定
            f.write(f"class {symbol}:\n    pass\n\n")
        else:
            # 関数の想定
            f.write(f"def {symbol}(*args, **kwargs):\n    pass\n\n")

def generate_skeleton_files():
    if not os.path.exists(UNDEF_FILE):
        print("[骨格生成] undefined_symbols.txt が存在しません。")
        return

    with open(UNDEF_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    pattern = re.compile(r": '(\w+)' not defined in (\w+\.py)")
    for line in lines:
        m = pattern.search(line)
        if m:
            symbol, file = m.group(1), m.group(2)
            target_file = os.path.join(FOLDER, file)
            add_skeleton_to_file(target_file, symbol)
            print(f"[骨格生成] {target_file} に {symbol} の骨格を追加")

if __name__ == "__main__":
    generate_skeleton_files()
