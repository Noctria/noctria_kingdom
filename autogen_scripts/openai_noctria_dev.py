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
UNDEF_SYMBOLS_FILE = "autogen_scripts/undefined_symbols.txt"
GEN_PROMPT_FILE = "autogen_scripts/ai_prompt_fix_missing.txt"
PROMPT_FIXER = "autogen_scripts/gen_prompt_for_undefined_symbols.py"

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

# ...（省略）既存のヘルパー関数群はそのまま...

# === ここまで現状コードと同じ。次が追記部分！ ===

async def run_pytest_fullcycle():
    """pytest→fail時は未定義検出＆AI自動修復ループ"""
    while True:
        passed, total, failed, details, log = await asyncio.to_thread(run_pytest_and_collect_detail, OUTPUT_DIR)
        print(f"pytest: 合格={passed} / 総数={total} / 失敗={failed}")
        if failed == 0:
            return True, log
        # --- 未定義シンボル解析＆AIリペア自動注入 ---
        print("pytest失敗。未定義シンボル検出→AI自動補完を試みます。")
        # 1. 未定義検出
        subprocess.run(["python3", "autogen_scripts/find_undefined_symbols.py"], check=True)
        # 2. AIリペア用プロンプト生成
        subprocess.run(["python3", PROMPT_FIXER], check=True)
        # 3. AIプロンプトをOpenAIへ投入→返答でファイル自動修復
        with open(GEN_PROMPT_FILE, "r", encoding="utf-8") as f:
            prompt = f.read()
        ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print("AI修復指示プロンプトを投げます...")
        repair_resp = await asyncio.to_thread(
            lambda: ai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
            )
        )
        response = repair_resp.choices[0].message.content
        files = split_files_from_response(response)
        if not files:
            print("AIリペア: 新規ファイル認識なし→ai_repair_output.pyへ保存")
            fname = os.path.join(OUTPUT_DIR, "ai_repair_output.py")
            save_ai_generated_file(fname, response)
        else:
            for fname, content in files.items():
                file_path = os.path.join(OUTPUT_DIR, fname)
                save_ai_generated_file(file_path, content)
                print(f"AI修復ファイル上書き: {file_path}")
        # Commit
        git_commit_and_push(OUTPUT_DIR, "[auto-repair] AI undefined symbol repair")
        # pytestを再度ループ
        print("pytestを再実行します…")
        await asyncio.sleep(1)  # 連続実行でAPI叩きすぎ防止

async def multi_agent_loop(client, max_turns=10):
    consecutive_fails = 0
    for turn in range(max_turns):
        print(f"\n=== Turn {turn+1} ===")
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
                        file_path = os.path.join(OUTPUT_DIR, fname)
                        save_ai_generated_file(file_path, content)
                        print(f"{role} AIのコード保存: {file_path}")
                        log_message(f"{role} AIのコード保存: {file_path}")

                commit_message = f"{role} AI generated files - turn {turn+1}"
                if not git_commit_and_push(OUTPUT_DIR, commit_message):
                    print(f"警告: Git連携に失敗しました。手動でコミットを確認してください。")

                if role == "test":
                    # --- pytest詳細を収集し、失敗したら自動修復ループへ ---
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
                        # ======== 【ここで自動修復フェーズへ突入】 ========
                        print("テスト失敗→AI自動修復ループに入ります！")
                        await run_pytest_fullcycle()
                        # pytestパスしたら次のロールに進む
                        passed, total, failed, details, log = await asyncio.to_thread(run_pytest_and_collect_detail, OUTPUT_DIR)
                        pytest_results.update(dict(
                            passed_tests=passed,
                            total_tests=total,
                            failed=failed > 0,
                            fail_reason=details[0]['message'][:100] if details and failed > 0 else None,
                            details=details,
                            pytest_log=log
                        ))
                        if failed > 0:
                            error_in_turn = True

                    feedback = f"テスト結果: {'成功' if pytest_results['failed'] == 0 else '失敗'}\nログ:\n{pytest_results['pytest_log']}"
                    messages["review"].append({"role": "user", "content": feedback})

        # ...（この後は既存通り：DB記録・人間承認フロー）...
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
