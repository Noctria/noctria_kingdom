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

        # 厳密なクラス・関数定義の正規表現パターン
        class_pattern = re.compile(rf"^class\s+{re.escape(symbol)}\b", re.MULTILINE)
        def_pattern = re.compile(rf"^def\s+{re.escape(symbol)}\b", re.MULTILINE)
        const_pattern = re.compile(rf"^{re.escape(symbol)}\s*=", re.MULTILINE)

        if class_pattern.search(content) or def_pattern.search(content) or const_pattern.search(content):
            # すでに骨格あり
            return

        f.seek(0, os.SEEK_END)
        if symbol.isupper():
            # 定数（Noneにしておく）
            f.write(f"{symbol} = None  # TODO: 適切な値に変更\n\n")
        elif symbol[0].isupper():
            # クラス骨格
            f.write(f"class {symbol}:\n    def __init__(self):\n        pass\n\n")
        else:
            # 関数骨格
            f.write(f"def {symbol}(*args, **kwargs):\n    pass\n\n")

def generate_skeleton_files():
    if not os.path.exists(UNDEF_FILE):
        print("[骨格生成] undefined_symbols.txt が存在しません。")
        return

    with open(UNDEF_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    pattern = re.compile(r": '(\w+)' not defined in (\w+\.py)")
    count = 0
    for line in lines:
        m = pattern.search(line)
        if m:
            symbol, file = m.group(1), m.group(2)
            target_file = os.path.join(FOLDER, file)
            add_skeleton_to_file(target_file, symbol)
            print(f"[骨格生成] {target_file} に {symbol} の骨格を追加")
            count += 1

    if count == 0:
        print("[骨格生成] 追加すべき未定義シンボルが見つかりませんでした。")

if __name__ == "__main__":
    generate_skeleton_files()
