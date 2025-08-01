import os
import asyncio
import subprocess
import re
import platform
from dotenv import load_dotenv
from openai import OpenAI
import datetime
import sys

load_dotenv()

OUTPUT_DIR = "./generated_code"
LOG_FILE = "./generated_code/chat_log.txt"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def log_message(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

async def call_openai(client, messages):
    try:
        response = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
            )
        )
        return response.choices[0].message.content
    except Exception as e:
        log_message(f"API呼び出しエラー: {e}")
        print(f"API呼び出しエラー: {e}", file=sys.stderr)
        return None

def run_code_quality_checks(code_path: str) -> bool:
    try:
        result = subprocess.run(
            ["flake8", code_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"コード品質チェックエラー:\n{result.stdout}")
            return False
        return True
    except Exception as e:
        print(f"品質チェック実行例外: {e}")
        return False

def git_commit_push(file_path: str, message: str) -> bool:
    try:
        subprocess.run(["git", "add", file_path], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"Gitコミット＆プッシュ成功: {file_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Git操作エラー: {e}")
        return False

def split_files_from_response(response: str):
    pattern = r"# ファイル名:\s*(.+\.py)\s*\n"
    splits = re.split(pattern, response)
    files = {}
    i = 1
    while i < len(splits):
        filename = splits[i].strip()
        content = splits[i+1]
        files[filename] = content.strip()
        i += 2
    return files

def show_diff(old_file, new_file):
    if platform.system() == "Windows":
        cmd = ["fc", old_file, new_file]
    else:
        cmd = ["diff", "-u", old_file, new_file]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.stdout:
            print("==== 差分 ====")
            print(result.stdout)
        else:
            print("差分なし")
    except Exception as e:
        print(f"差分表示でエラー発生: {e}")

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEYが設定されていません。")

    client = OpenAI(api_key=api_key)

    design_prompt = (
        "あなたは戦略設計AIです。USD/JPYの自動トレードAIの戦略を詳細に設計してください。"
        "次に実装AIと対話しながら戦略を詰めていきます。"
        "生成するコードは複数ファイルに分割してください。"
        "ファイルの先頭には必ず以下の形式でファイル名を明記してください。"
        "例：\n# ファイル名: strategy.py\n\n# ファイル名: utils.py\n"
    )
    implementation_prompt = (
        "あなたは実装AIです。設計AIからの指示に基づいてコードを生成し、"
        "適宜改善提案を行ってください。"
        "生成するコードは複数ファイルに分割してください。"
        "ファイルの先頭には必ず以下の形式でファイル名を明記してください。"
        "例：\n# ファイル名: strategy.py\n\n# ファイル名: utils.py\n"
    )

    design_messages = [{"role": "user", "content": design_prompt}]
    implementation_messages = [{"role": "user", "content": implementation_prompt}]

    max_turns = 10
    prev_code_paths = []

    for turn in range(max_turns):
        print(f"\n--- Turn {turn+1} ---")

        design_response = await call_openai(client, design_messages)
        if design_response is None:
            print("設計AIの応答取得に失敗しました。処理を中断します。")
            break
        print("設計AI:", design_response)
        log_message(f"設計AI: {design_response}")
        design_messages.append({"role": "assistant", "content": design_response})

        implementation_messages.append({"role": "user", "content": design_response})

        implementation_response = await call_openai(client, implementation_messages)
        if implementation_response is None:
            print("実装AIの応答取得に失敗しました。処理を中断します。")
            break
        print("実装AI:", implementation_response)
        log_message(f"実装AI: {implementation_response}")
        implementation_messages.append({"role": "assistant", "content": implementation_response})

        design_messages.append({"role": "user", "content": implementation_response})

        files = split_files_from_response(implementation_response)
        if not files:
            code_filename = os.path.join(OUTPUT_DIR, f"turn_{turn+1}_generated_code.py")
            with open(code_filename, "w", encoding="utf-8") as f:
                f.write(f"# 自動生成コード - ターン {turn+1}\n")
                f.write(implementation_response)
            print(f"コードを保存しました: {code_filename}")
            log_message(f"コードを保存しました: {code_filename}")

            if prev_code_paths:
                show_diff(prev_code_paths[-1], code_filename)
            prev_code_paths.append(code_filename)

            passed = await asyncio.to_thread(run_code_quality_checks, code_filename)
            if not passed:
                print(f"ターン{turn+1}のコード品質に問題があります。改善をAIに要求してください。")
                log_message(f"ターン{turn+1}のコード品質に問題あり。")

            commit_message = f"Auto commit: generated code turn {turn+1}"
            git_commit_push(code_filename, commit_message)

        else:
            for fname, content in files.items():
                file_path = os.path.join(OUTPUT_DIR, fname)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"コードを保存しました: {file_path}")
                log_message(f"コードを保存しました: {file_path}")

                if prev_code_paths:
                    # 差分表示は直前に保存した同名ファイルのみ対応
                    prev_same = [p for p in prev_code_paths if os.path.basename(p) == fname]
                    if prev_same:
                        show_diff(prev_same[-1], file_path)
                prev_code_paths.append(file_path)

                passed = await asyncio.to_thread(run_code_quality_checks, file_path)
                if not passed:
                    print(f"{fname} のコード品質に問題があります。改善をAIに要求してください。")
                    log_message(f"{fname} のコード品質に問題あり。")

                commit_message = f"Auto commit: generated code turn {turn+1} file {fname}"
                git_commit_push(file_path, commit_message)

        print("コマンド入力: 続行=Enter, 終了=q, 一時停止=p, スキップ=s")
        user_input = await asyncio.to_thread(input)
        if user_input.strip().lower() == "q":
            print("ユーザーによる中断指示を受けました。処理を終了します。")
            break
        elif user_input.strip().lower() == "p":
            print("一時停止中。再開するにはEnterを押してください。")
            await asyncio.to_thread(input)
        elif user_input.strip().lower() == "s":
            print("このターンをスキップします。")
            continue

    print("\n=== 自動対話ワークフロー終了 ===")
    log_message("=== 自動対話ワークフロー終了 ===")

if __name__ == "__main__":
    asyncio.run(main())
