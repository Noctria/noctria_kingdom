#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas Strategist (v2.3)
- LLM等を用いて新たな取引戦略を自動生成し、評価・選定まで担うAI
- 生成/評価の標準出力・エラーを必ずファイルに記録
- 合格戦略ランキング（topN）も返却対応
"""

import subprocess
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from src.core.path_config import (
    VERITAS_GENERATE_SCRIPT, VERITAS_EVAL_LOG, VERITAS_EVALUATE_SCRIPT, LOGS_DIR
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class VeritasStrategist:
    """
    真理を探究し、新たな戦略を創り出す戦略立案官AI。
    """

    def __init__(self):
        logging.info("戦略立案官ヴェリタス、着任。真理の探求を始めます。")
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.generate_log_path = LOGS_DIR / "veritas_generate.log"
        self.evaluate_log_path = LOGS_DIR / "veritas_evaluate.log"

    def _save_subprocess_output(self, proc: subprocess.CompletedProcess, log_path: Path, desc: str = ""):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- {desc} [{datetime.now()}] ---\n")
                f.write("STDOUT:\n")
                f.write(proc.stdout if proc.stdout else "")
                f.write("\nSTDERR:\n")
                f.write(proc.stderr if proc.stderr else "")
                f.write("\n")
        except Exception as e:
            logging.error(f"{desc}ログ保存時にエラー: {e}")

    def propose(self, top_n: int = 5) -> Dict[str, Any]:
        """
        新たな戦略を生成・評価し、最良と判断したものを王に提案する。
        top_n: ランキング返却件数（合格戦略が少なければ全件）
        """
        # 1. 戦略生成
        try:
            logging.info("新たな戦略の創出を開始します…")
            res = subprocess.run(
                ["python", str(VERITAS_GENERATE_SCRIPT)],
                check=True, capture_output=True, text=True
            )
            self._save_subprocess_output(res, self.generate_log_path, "VERITAS GENERATE")
            logging.info("戦略の原石が生成されました。")
        except subprocess.CalledProcessError as e:
            self._save_subprocess_output(e, self.generate_log_path, "VERITAS GENERATE (FAILED)")
            error_message = f"戦略生成の儀で失敗しました。詳細: {e.stderr or e}"
            logging.error(error_message)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": error_message}

        # 2. 評価
        try:
            logging.info("生成された戦略の評価の儀を開始します…")
            res = subprocess.run(
                ["python", str(VERITAS_EVALUATE_SCRIPT)],
                check=True, capture_output=True, text=True
            )
            self._save_subprocess_output(res, self.evaluate_log_path, "VERITAS EVALUATE")
            logging.info("評価の儀が完了しました。")
        except subprocess.CalledProcessError as e:
            self._save_subprocess_output(e, self.evaluate_log_path, "VERITAS EVALUATE (FAILED)")
            error_message = f"戦略評価の儀で失敗しました。詳細: {e.stderr or e}"
            logging.error(error_message)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": error_message}

        # 3. 最良戦略とランキング返却
        try:
            logging.info("評価結果から最良戦略とランキングを選定します…")
            with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
                results = json.load(f)
            passed_strategies = [r for r in results if r.get("passed")]
            if not passed_strategies:
                msg = "全ての戦略が評価基準を満たしませんでした。"
                logging.warning(msg)
                return {"type": "strategy_proposal", "status": "REJECTED", "detail": msg, "strategy_rankings": []}
            # ランキング生成（final_capital降順, 最大top_n件）
            rankings: List[dict] = sorted(
                passed_strategies,
                key=lambda r: r.get("final_capital", 0),
                reverse=True
            )[:top_n]
            best_strategy = rankings[0]
            logging.info(f"最良の戦略『{best_strategy.get('strategy')}』を選定しました。")
            return {
                "name": "Veritas",
                "type": "strategy_proposal",
                "status": "PROPOSED",
                "strategy_details": best_strategy,
                "strategy_rankings": rankings
            }
        except FileNotFoundError:
            msg = f"評価の記録（{VERITAS_EVAL_LOG}）が見つかりません。"
            logging.error(msg)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": msg, "strategy_rankings": []}
        except (json.JSONDecodeError, KeyError) as e:
            msg = f"評価の記録が破損 or 形式不正: {e}"
            logging.error(msg)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": msg, "strategy_rankings": []}

# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- 戦略立案官ヴェリタス、単独試練の儀を開始 ---")
    strategist = VeritasStrategist()
    proposal = strategist.propose(top_n=5)
    print("\n👑 王への進言（Veritas）:")
    print(json.dumps(proposal, indent=4, ensure_ascii=False))
    logging.info("\n--- 戦略立案官ヴェリタス、単独試練の儀を完了 ---")
