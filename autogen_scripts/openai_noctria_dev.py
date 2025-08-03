async def auto_fix_missing_symbols(client, max_attempts=5):
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        run_find_undefined_symbols()
        if not os.path.exists(UNDEF_FILE):
            print("[auto_fix] 未定義ファイルなし、ループ終了")
            break
        with open(UNDEF_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        print(f"[auto_fix] undefined_symbols.txt内容 (試行{attempts}回目):\n{content}")
        if not content or content.lower().startswith("=== 0 missing"):
            print("[auto_fix] 未定義なしと判断、ループ終了")
            break
        # AI補完呼び出しなど処理...
    else:
        print("[auto_fix] 最大試行回数到達、強制終了")
