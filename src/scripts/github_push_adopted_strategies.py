#!/usr/bin/env python3
# coding: utf-8

"""
📤 Adopted Strategy Pusher (v2.0)
- 評価ログをスキャンし、採用基準を満たした（passed=True）かつ、
- まだPushされていない（pushed=False）戦略をGitHubにPushする。
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_configから正しい変数名をインポート
from src.core.path_config import PROJECT_ROOT, STRATEGIES_DIR, ACT_LOG_DIR, VERITAS_EVAL_LOG

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')


def _run_git_command(cmd: list, cwd: Path):
    """指定されたディレクトリでGitコマンドを実行するヘルパー関数"""
    logging.info(f"Gitコマンドを実行します: {' '.join(cmd)}")
    try:
        # check=Trueでエラー時に例外を発生させる
        subprocess.run(cmd, check=True, cwd=cwd, capture_output=True, text=True)
        logging.info("✅ コマンド成功")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Gitコマンドの実行に失敗しました: {e.stderr}")
        raise  # エラーを再送出し、呼び出し元で処理できるようにする

def _push_strategy_to_github(strategy_file_path: Path):
    """単一の戦略ファイルをGitリポジトリにadd, commit, pushする"""
    if not strategy_file_path.exists():
        logging.error(f"Push対象の戦略ファイルが見つかりません: {strategy_file_path}")
        return

    repo_path = PROJECT_ROOT
    relative_path = strategy_file_path.relative_to(repo_path)
    commit_message = f"👑 採用戦略の公式記録: {strategy_file_path.name} ({datetime.utcnow().date()})"

    try:
        _run_git_command(["git", "add", str(relative_path)], cwd=repo_path)
        _run_git_command(["git", "commit", "-m", commit_message], cwd=repo_path)
        _run_git_command(["git", "push", "origin", "main"], cwd=repo_path)
        logging.info(f"戦略『{strategy_file_path.name}』が王国の公式記録（GitHub）に刻まれました。")
    except Exception as e:
        logging.error(f"戦略『{strategy_file_path.name}』の公式記録中にエラーが発生しました。: {e}")
        # 必要に応じて、失敗した場合のロールバック処理などをここに追加
        raise

def main():
    """
    Airflowから呼び出されるメイン関数。
    評価ログを読み込み、採用された戦略をGitHubにPushする。
    """
    logging.info("🚀 採用されし戦略の公式記録（GitHub Push）を開始します…")
    
    if not VERITAS_EVAL_LOG.exists():
        logging.warning(f"評価ログが見つかりません: {VERITAS_EVAL_LOG}。処理をスキップします。")
        return

    try:
        with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
            evaluation_results = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"評価ログの読み込みに失敗しました: {e}")
        return

    pushed_count = 0
    for result in evaluation_results:
        # 評価に合格し、まだPushされていない戦略のみを対象とする
        if result.get("passed") and not result.get("pushed"):
            strategy_filename = result.get("strategy")
            if not strategy_filename:
                continue

            # ✅ 修正: 正式な戦略はveritas_generatedからofficialに移動されている想定
            # このスクリプトは、`veritas_eval_dag`でofficialに移動されたものをPushする
            official_strategy_path = STRATEGIES_DIR / "official" / strategy_filename
            
            try:
                _push_strategy_to_github(official_strategy_path)
                # TODO: Push成功後、評価ログのpushedフラグを更新する処理が必要
                pushed_count += 1
            except Exception:
                # _push_strategy_to_github内でエラーログは出力済み
                logging.error(f"戦略『{strategy_filename}』のPushに失敗したため、次の戦略に進みます。")
                continue
    
    if pushed_count > 0:
        logging.info(f"📜 合計{pushed_count}件の戦略が王国の公式記録に刻まれました。")
    else:
        logging.info("📜 今回、新たに記録される戦略はありませんでした。")

if __name__ == "__main__":
    main()
