import os
import asyncio
import subprocess
import re
from dotenv import load_dotenv
from openai import OpenAI
import datetime
import sys
from uuid import uuid4

load_dotenv()

OUTPUT_DIR = "./generated_code"
LOG_FILE = os.path.join(OUTPUT_DIR, "chat_log.txt")
os.makedirs(OUTPUT_DIR, exist_ok=True)

KNOWLEDGE_PATH = "noctria_kingdom/docs/knowledge.md"
MMD_PATH = "noctria_kingdom/docs/Noctria連携図.mmd"

ENV_INFO = (
    "【実行環境・開発方針】\n"
    "- Windows PC上のWSL2（Ubuntu）＋ AirflowはDocker運用。\n"
    "- airflow_docker/ はDocker内、noctria_gui/はvenv_gui、noctria_kingdom/はvenv_noctria、autogenはautogen_venvで稼働。\n"
    "- パス・ボリューム共有、venv依存分離を常に意識。\n"
    "- Veritas（ML）は将来的にGPUクラウドサービス（AWS/GCP/Azure等）運用前提。\n"
    "- Noctriaの全機能はnoctria_gui/GUI管理ツールで集中管理できる設計徹底。\n"
    "- noctria_gui/配下HTMLはhud_style.cssに準拠したHUDスタイル統一。\n"
    "- 全プロダクトの最終判断・注文の可否はsrc/core/king_noctria.pyに集約。\n"
)

def load_file(path, max_chars=None):
    """ファイル内容を最大max_chars分だけ取得（全文渡すときはmax_chars=None）"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if max_chars:
                return content[:max_chars]
            return content
    except Exception:
        return ""

def prepend_env_and_knowledge_and_mmd(prompt: str) -> str:
    knowledge = load_file(KNOWLEDGE_PATH, max_chars=7000)
    mmd = load_file(MMD_PATH, max_chars=4000)
    return (
        f"{ENV_INFO}"
        f"\n--- knowledge.md（厳守すべきNoctria Kingdomナレッジベース）---\n{knowledge}\n"
        f"\n--- Noctria連携図.mmd（システム全体連携構造/ファイル依存）---\n{mmd}\n\n"
        f"{prompt}"
    )

ROLE_PROMPTS = {
    "design": prepend_env_and_knowledge_and_mmd(
        "あなたは戦略設計AIです。USD/JPYの自動トレードAIの戦略を詳細に設計してください。\n"
        "注文執行・最終判断は必ずsrc/core/king_noctria.pyに集約。\n"
        "Veritas ML設計・実装はGPUクラウドサービス上でのトレーニング・推論前提。\n"
        "Noctria Kingdomの各機能はnoctria_guiで集中管理、GUIはhud_style.cssのHUD統一デザイン厳守。\n"
        "複数ファイルに分割し、# ファイル名: filename.pyを明記。設計はpath_config.py一元化ルール厳守。\n"
        "設計説明は簡潔に。"
    ),
    "implement": prepend_env_and_knowledge_and_mmd(
        "設計AIの指示とNoctria連携図に従い実装コードを生成してください。\n"
        "パス指定は全てpath_config.pyからimportし直書き禁止。\n"
        "複数ファイル分割・# ファイル名: filename.py明記・PEP8/型アノテ必須・例外処理も適切に。\n"
        "GUI部分はhud_style.cssに則ったHUDデザインとすること。\n"
        "Veritas MLはクラウドGPU環境での動作を必ず考慮。\n"
    ),
    "test": prepend_env_and_knowledge_and_mmd(
        "設計AI・Noctria連携図.mmdを参考に各コンポーネントのpytest/unittestテストコードを生成してください。\n"
        "テストコードもパスは必ずpath_config.pyからimportすること。\n"
        "正常系・異常系・統合連携テストも含めること。\n"
    ),
    "review": prepend_env_and_knowledge_and_mmd(
        "生成コード・テストをNoctria連携図.mmd・knowledge.mdのルールに照らして評価し、"
        "全体最適化・リファクタ案も具体的に提案してください。\n"
        "パス直書きやルール違反があれば必ず指摘し修正案を明示。\n"
    ),
    "doc": prepend_env_and_knowledge_and_mmd(
        "Noctria連携図.mmd・knowledge.mdを元に構成説明、パス集中管理意義、環境構築手順を含むREADME/ドキュメントを自動生成してください。\n"
    ),
}

def log_message(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def git_commit_and_push(repo_dir: str, message: str) -> bool:
    try:
        subprocess.run(["git", "-C", repo_dir, "add", "."], check=True)
        subprocess.run(["git", "-C", repo_dir, "commit", "-m", message], check=True)
        subprocess.run(["git", "-C", repo_dir, "push"], check=True)
        log_message(f"Git commit & push succeeded: {message}")
        return True
    except subprocess.CalledProcessError as e:
        log_message(f"Git commit/push failed: {e}")
        return False

def build_file_header(filename: str, ai_name: str = "openai_noctria_dev.py", version: str = "v0.1.0"):
    now = datetime.datetime.now().isoformat()
    uid = str(uuid4())
    return (
        f"# ファイル名: {os.path.basename(filename)}\n"
        f"# バージョン: {version}\n"
        f"# 生成日時: {now}\n"
        f"# 生成AI: {ai_name}\n"
        f"# UUID: {uid}\n"
        "\n"
    )

def save_ai_generated_file(file_path: str, content: str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    header = build_file_header(file_path)
    if content.strip().startswith("# ファイル名:"):
        merged = content
    else:
        merged = header + content
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(merged)

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

async def call_openai(client, messages, retry=3, delay=2):
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
                    save_ai_generated_file(filename, response)
                    print(f"{role} AIのコード保存: {filename}")
                    log_message(f"{role} AIのコード保存: {filename}")
                else:
                    for fname, content in files.items():
                        file_path = os.path.join(OUTPUT_DIR, fname)
                        save_ai_generated_file(file_path, content)
                        print(f"{role} AIのコード保存: {file_path}")
                        log_message(f"{role} AIのコード保存: {file_path}")

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
