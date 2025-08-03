import os
import asyncio
import subprocess
import re
from dotenv import load_dotenv
from openai import OpenAI
import datetime
import sys

load_dotenv()

OUTPUT_DIR = "./generated_code"
LOG_FILE = os.path.join(OUTPUT_DIR, "chat_log.txt")
os.makedirs(OUTPUT_DIR, exist_ok=True)

ROLE_PROMPTS = {
    "design": (
        "あなたは戦略設計AIです。USD/JPYの自動トレードAIの戦略を詳細に設計してください。\n"
        "まず、noctria_kingdom/docs/Noctria連携図.mmdを読み込み、その内容（システム全体の連携構造、各ファイルやコンポーネントの関係性）を把握してください。\n"
        "その上で、この連携図に記載されたすべてのファイル群・コンポーネントの"
        "1. 構造上の問題点 2. 冗長な部分や重複機能 3. 改善・統合・リファクタ案 "
        "4. 保守性・拡張性のための設計提案 5. 不足しているテストやドキュメント などをレビューしてください。\n"
        "各ファイルの役割や依存関係についても可視化し、具体的な改良案・統合案を出してください。\n"
        "最初に連携図（Mermaidファイル）の内容を出力し、そのあとにレビューと提案を出力してください。"
        "複数ファイルに分割生成してください。ファイルの先頭に必ず「# ファイル名: filename.py」を記載してください。\n"
        "戦略設計は実装に必要な関数やクラスの構造、処理の流れを明確に示し、拡張や修正が容易な設計にしてください。\n"
        "設計説明は簡潔かつ具体的に。過度に冗長にならないように注意してください。"
    ),
    "implement": (
        "設計AIの指示とnoctria_kingdom/docs/Noctria連携図.mmdに従い、改良された構造・設計に基づく実装コードを生成してください。\n"
        "あなたは実装AIです。設計AIからの指示に基づきコードを生成し、改善提案をしてください。\n"
        "複数ファイルに分割し、ファイル先頭に「# ファイル名: filename.py」を必ず記載してください。\n"
        "コードは説明文なしで、実行可能な純粋なPythonコードのみを返してください。\n"
        "PEP8準拠かつ型アノテーションを必ず付けてください。\n"
        "例外処理を適切に実装してください。\n"
        "冗長なコメントは避け、必要最小限にとどめてください。\n"
        "依存パッケージがあればrequirements.txtを作成してください。\n"
        "ファイルの文字コードはUTF-8であることを保証してください。\n"
        "コード整形ツール（Black, isort）を通した後の状態を意識してください。"
    ),
    "test": (
        "Noctria連携図.mmdおよび設計AIのレビューをもとに、各コンポーネントのテストコードを生成してください。\n"
        "冗長・重複・境界・エラーケース・統合的な連携テストもカバーしてください。"
        "あなたはテストAIです。生成されたコードに対する単体テストコードを作成してください。\n"
        "テストコードはunittestまたはpytest形式で統一してください。\n"
        "各機能の正常系テストに加え、境界値や異常系のテストケースも含めてください。\n"
        "テストコードは別ファイルに分割し、ファイル先頭に「# ファイル名: test_filename.py」を必ず記載してください。\n"
        "テストコード内で必要な前処理・後処理（setUp/tearDown）も適切に記述してください。\n"
        "テストコードは読みやすく保守しやすい構造にしてください。"
    ),
    "review": (
        "生成コードとテストを連携図.mmdに照らして評価し、全体最適化や構造上の統合・リファクタ案も追加で指摘してください。"
        "あなたはレビューAIです。実装AIとテストAIの生成したコードとテスト結果を評価してください。\n"
        "コードのバグ、ロジックの問題点を指摘し、具体的な改善提案を述べてください。\n"
        "リファクタリングやパフォーマンス改善、セキュリティ上の懸念（例：SQLインジェクション）も検討してください。\n"
        "コードの拡張性や保守性に関するコメントも含めてください。\n"
        "テスト結果からのフィードバックも分析し、必要ならばコードやテストの追加改善を指示してください。"
    ),
    "doc": (
        "Noctria連携図.mmdをもとに、全体構成の説明、ファイル相互関係のMermaid可視化、環境構築・実行手順も含むドキュメントを自動生成してください。"
        "あなたはドキュメントAIです。生成コードのAPIドキュメントやREADMEを自動生成してください。\n"
        "APIドキュメントはOpenAPI仕様やdocstring形式で詳細かつ正確に作成してください。\n"
        "READMEには環境構築手順、使い方、依存関係、注意点をわかりやすく記載してください。\n"
        "関数やクラスのdocstringも適切に自動生成してください。"
    ),
}

def log_message(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def git_commit_and_push(repo_dir: str, message: str) -> bool:
    """
    指定ディレクトリでgit add・commit・pushを実行する。

    Args:
        repo_dir: Gitリポジトリのルートディレクトリ
        message: コミットメッセージ

    Returns:
        成功したらTrue、失敗したらFalse
    """
    try:
        subprocess.run(["git", "-C", repo_dir, "add", "."], check=True)
        subprocess.run(["git", "-C", repo_dir, "commit", "-m", message], check=True)
        subprocess.run(["git", "-C", repo_dir, "push"], check=True)
        log_message(f"Git commit & push succeeded: {message}")
        return True
    except subprocess.CalledProcessError as e:
        log_message(f"Git commit/push failed: {e}")
        return False

async def call_openai(client, messages, retry=3, delay=2):
    """
    OpenAI APIを呼び出す関数（リトライ対応）

    Args:
        client: OpenAIクライアントインスタンス
        messages: チャットメッセージリスト
        retry: 最大リトライ回数（デフォルト3回）
        delay: リトライ間隔（秒）

    Returns:
        API応答のテキスト（str）

    Raises:
        Exception: 全リトライ失敗時に例外を再送出
    """
    for attempt in range(retry):
        try:
            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            log_message(f"API呼び出しエラー(試行 {attempt+1}/{retry}): {e}")
            print(f"API呼び出しエラー(試行 {attempt+1}/{retry}): {e}", file=sys.stderr)
            if attempt + 1 == retry:
                raise
            await asyncio.sleep(delay)

def split_files_from_response(response: str):
    pattern = r"# ファイル名:\s*(.+?\.py)\s*\n"
    splits = re.split(pattern, response)
    files = {}
    i = 1
    while i < len(splits):
        filename = splits[i].strip()
        content = splits[i + 1]
        files[filename] = content.strip()
        i += 2
    return files

def run_pytest(test_dir: str) -> (bool, str):
    try:
        result = subprocess.run(
            ["pytest", test_dir, "--maxfail=1", "--disable-warnings", "-q"],
            capture_output=True,
            text=True,
            timeout=60
        )
        success = (result.returncode == 0)
        return success, result.stdout + "\n" + result.stderr
    except Exception as e:
        return False, f"pytest実行例外: {e}"

async def multi_agent_loop(client, max_turns=5):
    messages = {role: [{"role": "user", "content": prompt}] for role, prompt in ROLE_PROMPTS.items()}

    for turn in range(max_turns):
        print(f"\n=== Turn {turn+1} ===")
        order = ["design", "implement", "test", "review", "doc"]

        for i, role in enumerate(order):
            print(f"\n--- {role.upper()} AI ---")
            response = await call_openai(client, messages[role])
            if response is None:
                print(f"{role} AIの応答取得に失敗。処理中断。")
                return
            print(response)
            log_message(f"{role} AI: {response}")
            messages[role].append({"role": "assistant", "content": response})

            next_role = order[(i + 1) % len(order)]
            messages[next_role].append({"role": "user", "content": response})

            if role in ("implement", "test", "doc"):
                files = split_files_from_response(response)
                if not files:
                    filename = os.path.join(OUTPUT_DIR, f"{role}_turn{turn+1}.py")
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(response)
                    print(f"{role} AIのコード保存: {filename}")
                    log_message(f"{role} AIのコード保存: {filename}")
                else:
                    for fname, content in files.items():
                        file_path = os.path.join(OUTPUT_DIR, fname)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        print(f"{role} AIのコード保存: {file_path}")
                        log_message(f"{role} AIのコード保存: {file_path}")

                # Git連携処理を追加
                commit_message = f"{role} AI generated files - turn {turn+1}"
                if not git_commit_and_push(OUTPUT_DIR, commit_message):
                    print(f"警告: Git連携に失敗しました。手動でコミットを確認してください。")

                if role == "test":
                    success, test_log = await asyncio.to_thread(run_pytest, OUTPUT_DIR)
                    print(f"テスト実行結果 success={success}")
                    print(test_log)
                    log_message(f"テスト結果:\n{test_log}")

                    feedback = f"テスト結果: {'成功' if success else '失敗'}\nログ:\n{test_log}"
                    messages["review"].append({"role": "user", "content": feedback})

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
