import os
import asyncio
import subprocess
import re
from dotenv import load_dotenv
from openai import OpenAI
import datetime
import sys
from uuid import uuid4
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "utils")))
from cycle_logger import insert_turn_history

load_dotenv()

OUTPUT_DIR = "./generated_code"
LOG_FILE = os.path.join(OUTPUT_DIR, "chat_log.txt")
os.makedirs(OUTPUT_DIR, exist_ok=True)

KNOWLEDGE_PATH = "noctria_kingdom/docs/knowledge.md"
MMD_PATH = "noctria_kingdom/docs/Noctria連携図.mmd"

# --- 未定義シンボル補完用のパス ---
UNDEF_FILE = "autogen_scripts/undefined_symbols.txt"
PROMPT_OUT = "autogen_scripts/ai_prompt_fix_missing.txt"
GEN_PROMPT_SCRIPT = "autogen_scripts/gen_prompt_for_undefined_symbols.py"
FIND_UNDEF_SCRIPT = "autogen_scripts/find_undefined_symbols.py"

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
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if max_chars:
                return content[:max_chars]
            return content
    except Exception:
        return ""

def build_prompt_with_latest_knowledge(prompt: str) -> str:
    knowledge = load_file(KNOWLEDGE_PATH)
    mmd = load_file(MMD_PATH)
    return (
        f"{ENV_INFO}"
        f"\n--- knowledge.md（厳守すべきNoctria Kingdomナレッジベース・最新版自動反映）---\n{knowledge}\n"
        f"\n--- Noctria連携図.mmd（全体構造/依存/バージョン）---\n{mmd}\n\n"
        f"{prompt}"
    )

def role_prompt_template(role):
    base_req = (
        "・knowledge.md/Noctria連携図を毎ターン最新で反映せよ。\n"
        "・全プロンプト/生成物は最新ルール・AI倫理/説明責任/バージョン管理/A/Bテスト/ロールバック/人間承認/セキュリティ/障害対応など全ガイドラインを必ず遵守せよ。\n"
        "・各ターンで生成物/理由/差分を履歴DBへ記録・説明を添付し、進化の証跡とすること。\n"
        "・【重要】すべてのPythonファイルは必ず「generated_code/」直下に出力し、サブディレクトリや「generated_code/」の重複は絶対に作らないこと。ファイル名にはディレクトリ名を含めず、例: data_collector.py 形式のみ許可。\n"
    )
    if role == "design":
        return (
            base_req +
            "あなたはAI設計責任者です。USD/JPY自動トレードAIの戦略設計をNoctriaガイドラインに従い厳格に設計し、設計根拠・バージョン・ABテスト要否・説明責任コメントも必ず明記。\n"
            "注文執行・最終判断は必ずsrc/core/king_noctria.pyに集約すること。\n"
            "複数ファイル分割時は # ファイル名: filename.py を必ず明示。\n"
        )
    if role == "implement":
        return (
            base_req +
            "設計AI指示・Noctria連携図・ガイドライン・最新knowledge.mdを厳守し、コードを生成せよ。\n"
            "パス指定は全てpath_config.pyからimportし、バージョン/説明/ABテストラベル/倫理コメントを各ファイルに付与。\n"
            "GUIはhud_style.cssのHUD準拠。\n"
        )
    if role == "test":
        return (
            base_req +
            "【自動テスト設計・品質ガイドライン】\n"
            "- テストファイルには**Pythonコードのみ**を記載し、絶対にマークダウン記法（```や```pythonなど）は使わないこと。\n"
            "- 全テスト関数のうち**50%以上は「正常系（合格パターン）」**とすること。\n"
            "- 正常系: 実際に合格する出力をassertするテストを明記（例：add(2,3)==5）。\n"
            "- 異常系: 不正な入力や例外発生のみを期待するパターンは全体の3割まで。\n"
            "- 異常系は必ずwith pytest.raises(...)構文で、try-except/except Exceptionは禁止。\n"
            "- テスト関数名は `test_機能_説明` とし、各関数の冒頭に # 目的: ... # 期待結果: ... の説明コメントを記載。\n"
            "- 冗長なcatchや似たような異常系ばかり量産しないこと。\n"
            "- 各テストは実装済みの関数や本体コードを呼び出し、assertで合格/失敗を判定すること。\n"
            "- テスト以外の設計や冗長な説明はテストファイルに含めないこと。\n"
            "【出力形式】\n"
            "- 複数のテスト関数を1ファイルにまとめる\n"
            "- # ファイル名: test_XXXXX.py から始めて出力すること\n"
            "- pytest/unittest形式で記述すること\n"
        )
    if role == "review":
        return (
            base_req +
            "生成物・テストをknowledge.md/連携図/全ガイドラインに照らして厳格レビューし、リファクタ案/退行検知/倫理逸脱や障害があれば即時警告・是正策もコメントし履歴化。\n"
        )
    if role == "doc":
        return (
            base_req +
            "Noctria連携図・knowledge.mdをもとに構成説明・パス集中管理意義・バージョン履歴・AI自動化・倫理運用手順をREADME/ドキュメントとして自動生成し、全てにバージョン/説明責任を付与。\n"
        )
    return base_req

def get_role_prompts():
    return {
        role: build_prompt_with_latest_knowledge(role_prompt_template(role))
        for role in ["design", "implement", "test", "review", "doc"]
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
        "# 説明責任: このファイルはNoctria Kingdomナレッジベース・ガイドライン・設計根拠を遵守し自動生成されています。\n"
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

def sanitize_filename(fname: str) -> str:
    fname = fname.replace("\\", "/")
    while fname.startswith("./"):
        fname = fname[2:]
    while fname.startswith("generated_code/"):
        fname = fname[len("generated_code/"):]
    # basenameのみでflat化（サブディレクトリ不可）
    return os.path.basename(fname)

def run_pytest_and_collect_detail(test_dir: str):
    import shutil
    report_file = os.path.join(test_dir, "pytest_result.json")
    cmd = ["pytest", test_dir, "--json-report", f"--json-report-file={report_file}", "--disable-warnings", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(report_file):
        return 0, 0, 0, [], result.stdout + "\n" + result.stderr
    try:
        with open(report_file, "r") as f:
            report = json.load(f)
        pass_count = report["summary"].get("passed", 0)
        fail_count = report["summary"].get("failed", 0)
        error_count = report["summary"].get("errors", 0)
        total = pass_count + fail_count + error_count
        error_details = []
        for t in report.get("tests", []):
            detail = {
                "name": t.get("nodeid"),
                "outcome": t.get("outcome"),
                "message": t.get("call", {}).get("longrepr", "") if t.get("call") else ""
            }
            error_details.append(detail)
        if os.path.exists(report_file):
            try:
                os.remove(report_file)
            except Exception:
                pass
        return pass_count, total, fail_count + error_count, error_details, result.stdout + "\n" + result.stderr
    except Exception as e:
        return 0, 0, 0, [], f"pytest解析エラー: {e}\n{result.stdout}\n{result.stderr}"

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

# --- 未定義シンボル自動注入ロジック ---

def run_find_undefined_symbols():
    subprocess.run(["python3", FIND_UNDEF_SCRIPT], check=True)

def run_gen_prompt_for_undefined_symbols():
    subprocess.run(["python3", GEN_PROMPT_SCRIPT], check=True)
    with open(PROMPT_OUT, "r", encoding="utf-8") as f:
        return f.read()

async def call_openai_for_missing_symbols(client, prompt):
    messages = [{"role": "user", "content": prompt}]
    for attempt in range(3):
        try:
            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                )
            )
            return response.choices[0].message.content
        except Exception:
            await asyncio.sleep(2)
    raise RuntimeError("AI補完失敗")

def save_and_commit_ai_files(ai_response):
    files = split_files_from_response(ai_response)
    if not files:
        print("AI出力から保存すべきファイルが検出できませんでした")
        return
    for fname, content in files.items():
        flat_fname = sanitize_filename(fname)
        file_path = os.path.join(OUTPUT_DIR, flat_fname)
        save_ai_generated_file(file_path, content)
        print(f"[未定義補完] AIのコード保存: {file_path}")
        log_message(f"[未定義補完] AIのコード保存: {file_path}")
    git_commit_and_push(OUTPUT_DIR, "fix: 自動未定義シンボル補完")

async def auto_fix_missing_symbols(client):
    while True:
        run_find_undefined_symbols()
        if not os.path.exists(UNDEF_FILE):
            break
        with open(UNDEF_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content or content.lower().startswith("=== 0 missing"):
                break
        prompt = run_gen_prompt_for_undefined_symbols()
        ai_response = await call_openai_for_missing_symbols(client, prompt)
        save_and_commit_ai_files(ai_response)
        # もう一度ループして、まだ未定義が残っていないか再チェック

async def multi_agent_loop(client, max_turns=10):
    consecutive_fails = 0
    for turn in range(max_turns):
        print(f"\n=== Turn {turn+1} ===")

        # --- 1. テスト・実装前に未定義シンボル自動補完（全消えるまで）---
        await auto_fix_missing_symbols(client)

        order = ["design", "implement", "test", "review", "doc"]
        role_prompts = get_role_prompts()
        messages = {role: [{"role": "user", "content": role_prompts[role]}] for role in order}

        error_in_turn = False
        pytest_results = {}

        for i, role in enumerate(order):
            print(f"\n--- {role.upper()} AI ---")
            try:
                response = await call_openai(client, messages[role])
            except Exception as e:
                print(f"{role} AIの応答取得に失敗。処理中断。")
                error_in_turn = True
                log_message(f"ERROR: {role} fail {e}")
                break

            if response is None:
                print(f"{role} AIの応答がありません。")
                error_in_turn = True
                break
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
                        flat_fname = sanitize_filename(fname)
                        file_path = os.path.join(OUTPUT_DIR, flat_fname)
                        save_ai_generated_file(file_path, content)
                        print(f"{role} AIのコード保存: {file_path}")
                        log_message(f"{role} AIのコード保存: {file_path}")

                commit_message = f"{role} AI generated files - turn {turn+1}"
                if not git_commit_and_push(OUTPUT_DIR, commit_message):
                    print(f"警告: Git連携に失敗しました。手動でコミットを確認してください。")

                if role == "test":
                    passed, total, failed, details, log = await asyncio.to_thread(run_pytest_and_collect_detail, OUTPUT_DIR)
                    print(f"テスト実行結果: 合格={passed} / 総数={total} / 失敗={failed}")
                    log_message(f"テスト結果:\n{log}")
                    pytest_results = dict(
                        passed_tests=passed,
                        total_tests=total,
                        failed=failed > 0,
                        fail_reason=details[0]['message'][:100] if details and failed > 0 else None,
                        details=details,
                        pytest_log=log
                    )
                    if failed > 0:
                        error_in_turn = True

                    feedback = f"テスト結果: {'成功' if failed == 0 else '失敗'}\nログ:\n{log}"
                    messages["review"].append({"role": "user", "content": feedback})

            # --- 2. テスト・実装の後にも未定義シンボル自動補完 ---
            await auto_fix_missing_symbols(client)

        # 進捗DB保存
        try:
            generated_files = len([
                f for f in os.listdir(OUTPUT_DIR)
                if os.path.isfile(os.path.join(OUTPUT_DIR, f))
            ])
            passed_tests = pytest_results.get("passed_tests", 0)
            total_tests = pytest_results.get("total_tests", 0)
            review_comments = 1
            failed = error_in_turn
            fail_reason = pytest_results.get("fail_reason") if failed else None
            extra_info = {
                "turn": turn+1,
                "ai_roles": order,
                "pytest_details": pytest_results.get("details", []),
                "pytest_log": pytest_results.get("pytest_log", ""),
                "note": "auto-recorded from openai_noctria_dev.py (pytest詳細収集版)"
            }
            finished_at = datetime.datetime.now()

            insert_turn_history(
                turn_number=turn+1,
                passed_tests=passed_tests,
                total_tests=total_tests,
                generated_files=generated_files,
                review_comments=review_comments,
                failed=failed,
                fail_reason=fail_reason,
                extra_info=extra_info,
                finished_at=finished_at
            )
            print(f"[DB記録] ターン{turn+1} の実績をDB保存しました")
        except Exception as e:
            print(f"[DB記録エラー] ターン{turn+1}: {e}")

        if error_in_turn:
            consecutive_fails += 1
            if consecutive_fails >= 3:
                print("\n[ALERT] 3ターン連続エラー/品質退行を検出。AI自動生成を停止し、人間承認フローに移行します。")
                log_message("3連続エラーにより自動停止・人間承認待ち。")
                print("承認・指示があるまで続行しません。qで終了。Enterで再開可。")
                user_input = await asyncio.to_thread(input)
                if user_input.strip().lower() == "q":
                    print("ユーザーによる中断指示を受けました。終了します。")
                    break
                else:
                    consecutive_fails = 0
        else:
            consecutive_fails = 0

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
