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

ROLE_PROMPTS = {
    "design": (
        "あなたは戦略設計AIです。USD/JPYの自動トレードAIの戦略を詳細に設計してください。"
        "複数ファイルに分割生成してください。ファイルの先頭に必ず「# ファイル名: filename.py」を記載してください。"
    ),
    "implement": (
        "あなたは実装AIです。設計AIからの指示に基づきコードを生成し、改善提案をしてください。"
        "複数ファイル分割し、ファイル先頭に「# ファイル名: filename.py」を記載してください。"
    ),
    "test": (
        "あなたはテストAIです。生成コードに対する単体テストコードを作成してください。"
        "テストコードは別ファイルに分割してください。"
    ),
    "review": (
        "あなたはレビューAIです。コードとテスト結果を評価し、改善点を述べてください。"
    ),
    "doc": (
        "あなたはドキュメントAIです。APIドキュメントやREADMEを自動生成してください。"
    ),
}

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

async def multi_agent_loop(client, max_turns=5):
    # 初期メッセージを役割ごとにセット
    messages = {role: [{"role": "user", "content": prompt}] for role, prompt in ROLE_PROMPTS.items()}
    prev_code_paths = []

    for turn in range(max_turns):
        print(f"\n=== Turn {turn+1} ===")

        # 役割順に呼び出し、次役割のユーザーメッセージに前役割の応答を渡す
        order = ["design", "implement", "test", "review", "doc"]
        for i, role in enumerate(order):
            print(f"\n--- {role.upper()} AI ---")
            response = await call_openai(client, messages[role])
            if response is None:
                print(f"{role} AIの応答取得に失敗。処理を中断します。")
                return

            print(response)
            log_message(f"{role} AI: {response}")
            messages[role].append({"role": "assistant", "content": response})

            # 次の役割にこの応答をユーザーメッセージとして渡す
            next_role = order[(i + 1) % len(order)]
            messages[next_role].append({"role": "user", "content": response})

            # 生成コードの保存と品質チェック（implement, test, docのみ対応）
            if role in ("implement", "test", "doc"):
                files = split_files_from_response(response)
                if not files:
                    code_filename = os.path.join(OUTPUT_DIR, f"{role}_turn{turn+1}.py")
                    with open(code_filename, "w", encoding="utf-8") as f:
                        f.write(response)
                    print(f"{role} AIのコードを保存しました: {code_filename}")
                    log_message(f"{role} AIのコードを保存しました: {code_filename}")
                    prev_code_paths.append(code_filename)
                else:
                    for fname, content in files.items():
                        file_path = os.path.join(OUTPUT_DIR, fname)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        print(f"{role} AIのコードを保存しました: {file_path}")
                        log_message(f"{role} AIのコードを保存しました: {file_path}")
                        prev_code_paths.append(file_path)

        # ターン終了後ユーザー操作
        print("\nコマンド入力: 続行=Enter, 終了=q, 一時停止=p")
        user_input = await asyncio.to_thread(input)
        if user_input.strip().lower() == "q":
            print("ユーザーによる中断指示を受けました。終了します。")
            break
        elif user_input.strip().lower() == "p":
            print("一時停止中。再開にはEnterを押してください。")
            await asyncio.to_thread(input)

    print("\n=== 多役割AI対話ワークフロー終了 ===")
    log_message("=== 多役割AI対話ワークフロー終了 ===")

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEYが設定されていません。")

    client = OpenAI(api_key=api_key)
    await multi_agent_loop(client, max_turns=10)

if __name__ == "__main__":
    asyncio.run(main())
