#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas Strategist (v2.1)
- LLM等を用いて新たな取引戦略を自動生成し、評価・選定まで担うAI
- KingNoctriaと明確なインターフェイス形式で連携
"""

import subprocess
import json
import logging
from typing import Dict, Any

from src.core.path_config import (
    VERITAS_GENERATE_SCRIPT, VERITAS_EVAL_LOG, VERITAS_EVALUATE_SCRIPT
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class VeritasStrategist:
    """
    真理を探究し、新たな戦略を創り出す戦略立案官AI。
    """

    def __init__(self):
        logging.info("戦略立案官ヴェリタス、着任。真理の探求を始めます。")

    def propose(self) -> Dict[str, Any]:
        """
        新たな戦略を生成・評価し、最良と判断したものを王に提案する。
        出力形式: {"type": ..., "status": ..., ...} でAPI/Kingに返す
        """
        # 1. 戦略生成
        try:
            logging.info("新たな戦略の創出を開始します…")
            res = subprocess.run(
                ["python", str(VERITAS_GENERATE_SCRIPT)],
                check=True, capture_output=True, text=True
            )
            logging.info("戦略の原石が生成されました。")
        except subprocess.CalledProcessError as e:
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
            logging.info("評価の儀が完了しました。")
        except subprocess.CalledProcessError as e:
            error_message = f"戦略評価の儀で失敗しました。詳細: {e.stderr or e}"
            logging.error(error_message)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": error_message}

        # 3. 最良戦略の選定
        try:
            logging.info("評価結果から最良戦略を選定します…")
            with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
                results = json.load(f)
            passed_strategies = [r for r in results if r.get("passed")]
            if not passed_strategies:
                msg = "全ての戦略が評価基準を満たしませんでした。"
                logging.warning(msg)
                return {"type": "strategy_proposal", "status": "REJECTED", "detail": msg}
            best_strategy = max(passed_strategies, key=lambda r: r.get("final_capital", 0))
            logging.info(f"最良の戦略『{best_strategy.get('strategy')}』を選定しました。")
            return {
                "name": "Veritas",
                "type": "strategy_proposal",
                "status": "PROPOSED",
                "strategy_details": best_strategy
            }
        except FileNotFoundError:
            msg = f"評価の記録（{VERITAS_EVAL_LOG}）が見つかりません。"
            logging.error(msg)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": msg}
        except (json.JSONDecodeError, KeyError) as e:
            msg = f"評価の記録が破損 or 形式不正: {e}"
            logging.error(msg)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": msg}

# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- 戦略立案官ヴェリタス、単独試練の儀を開始 ---")
    strategist = VeritasStrategist()
    proposal = strategist.propose()
    print("\n👑 王への進言（Veritas）:")
    print(json.dumps(proposal, indent=4, ensure_ascii=False))
    logging.info("\n--- 戦略立案官ヴェリタス、単独試練の儀を完了 ---")
