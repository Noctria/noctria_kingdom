import argparse
import json
from core import path_config

def verify_paths(strict=False, show_paths=False, category=None, output_json=False):
    paths = []
    results = []

    if category:
        if category not in path_config.CATEGORY_MAP:
            err_msg = f"❌ カテゴリ '{category}' は存在しません。利用可能カテゴリ一覧は --list-categories で確認できます。"
            if output_json:
                print(json.dumps({"success": False, "error": err_msg}, indent=2, ensure_ascii=False))
            else:
                print(err_msg)
            return
        paths = path_config.CATEGORY_MAP[category]
    else:
        for group in path_config.CATEGORY_MAP.values():
            paths.extend(group)

    all_ok = True
    for p in paths:
        entry = {"path": str(p), "exists": p.exists()}
        if strict:
            if p.is_dir():
                entry["type"] = "dir"
            elif p.is_file():
                entry["type"] = "file"
            else:
                entry["type"] = "unknown"
        results.append(entry)

        if not p.exists():
            all_ok = False
            if not output_json:
                print(f"❌ 不在: {p}")
        else:
            if strict and entry.get("type") == "unknown":
                all_ok = False
                if not output_json:
                    print(f"⚠️ 不明な型: {p}")
            elif not output_json and show_paths:
                print(f"✅ OK: {p}")

    if output_json:
        print(json.dumps({
            "success": all_ok,
            "category": category or "all",
            "result": results
        }, indent=2, ensure_ascii=False))
    else:
        print("🎉 すべてのパスが正常に存在しています。" if all_ok else "🚨 一部のパスに問題があります。")

def list_categories():
    print("📚 利用可能なカテゴリ一覧:")
    for name, paths in path_config.CATEGORY_MAP.items():
        print(f"  ▶ {name}（{len(paths)}個）:")
        for p in paths:
            print(f"     - {p}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="🔍 Noctria Kingdom パス構成検査ツール")
    parser.add_argument("--strict", action="store_true", help="ディレクトリ種別まで厳密に検査")
    parser.add_argument("--show-paths", action="store_true", help="全パスを表示（--json 無効時のみ）")
    parser.add_argument("--category", type=str, help="検査対象カテゴリを指定（例: core, ai, gui）")
    parser.add_argument("--list-categories", action="store_true", help="利用可能カテゴリ一覧を表示")
    parser.add_argument("--json", action="store_true", help="結果を JSON 形式で出力")

    args = parser.parse_args()

    if args.list_categories:
        list_categories()
    else:
        verify_paths(
            strict=args.strict,
            show_paths=args.show_paths,
            category=args.category,
            output_json=args.json
        )
