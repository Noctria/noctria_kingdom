import os

def search_redirects(directory: str):
    # 検索対象となるリダイレクトのパターン
    redirect_patterns = [
        "RedirectResponse",  # FastAPI のリダイレクト
        "HTTPException",      # HTTPException でリダイレクトが発生する場合も
        "return redirect",    # Python標準のリダイレクト記法
        "redirect("/statistics"  # URLに関するリダイレクト設定
    ]

    # ファイル走査
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):  # Pythonファイルのみ
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                    # ファイル内でリダイレクトのパターンを探す
                    for line_num, line in enumerate(lines, 1):
                        if any(pattern in line for pattern in redirect_patterns):
                            print(f"リダイレクトが見つかりました: {file_path} (行 {line_num})")
                            print(f"コード: {line.strip()}")
                            print("-" * 50)

if __name__ == "__main__":
    noctria_gui_dir = "/mnt/d/noctria_kingdom/noctria_gui"  # `noctria_gui` のパス
    search_redirects(noctria_gui_dir)
