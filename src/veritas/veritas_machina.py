#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas Strategist (v2.0)
- LLMを用いて新たな取引戦略を自動で生成し、評価・選定までを行うAI
"""

import subprocess
import json
import logging
from typing import Dict

# --- 王国の基盤モジュールをインポート ---
from src.core.path_config import VERITAS_GENERATE_SCRIPT, VERITAS_EVAL_LOG, VERITAS_EVALUATE_SCRIPT

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')


class VeritasStrategist:
    """
    真理を探究し、新たな戦略を創り出す戦略立案官AI。
    """

    def __init__(self):
        """コンストラクタ"""
        logging.info("戦略立案官ヴェリタス、着任。真理の探求を始めます。")

    def propose(self) -> Dict:
        """
        新たな戦略を生成・評価し、最良と判断したものを王に提案する。
        """
        # 1. 戦略生成の儀
        try:
            logging.info("新たな戦略の創出を開始します…")
            # 外部スクリプトを呼び出して戦略を生成
            subprocess.run(["python", str(VERITAS_GENERATE_SCRIPT)], check=True, capture_output=True, text=True)
            logging.info("戦略の原石が生成されました。")
        except subprocess.CalledProcessError as e:
            error_message = f"戦略生成の儀で失敗しました。詳細: {e.stderr}"
            logging.error(error_message)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": error_message}

        # 2. 評価の儀
        try:
            logging.info("生成された戦略の真価を問う、評価の儀を開始します…")
            # 評価用スクリプトを呼び出し
            subprocess.run(["python", str(VERITAS_EVALUATE_SCRIPT)], check=True, capture_output=True, text=True)
            logging.info("評価の儀が完了しました。")
        except subprocess.CalledProcessError as e:
            error_message = f"戦略評価の儀で失敗しました。詳細: {e.stderr}"
            logging.error(error_message)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": error_message}

        # 3. 最良戦略の選定
        try:
            logging.info("評価結果を吟味し、最良の策を選定します…")
            with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
                results = json.load(f)

            passed_strategies = [r for r in results if r.get("passed")]
            if not passed_strategies:
                logging.warning("有望な戦略は見つかりませんでした。再度の創出が必要です。")
                return {"type": "strategy_proposal", "status": "REJECTED", "detail": "全ての戦略が評価基準を満たしませんでした。"}

            # 最終資産が最も高い戦略を最良とする
            best_strategy = max(passed_strategies, key=lambda r: r.get("final_capital", 0))
            
            logging.info(f"最良の戦略『{best_strategy.get('strategy')}』を選定しました。")
            return {
                "name": "Veritas",
                "type": "strategy_proposal",
                "status": "PROPOSED",
                "strategy_details": best_strategy
            }
        except FileNotFoundError:
            error_message = f"評価の記録（{VERITAS_EVAL_LOG}）が見つかりません。"
            logging.error(error_message)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": error_message}
        except (json.JSONDecodeError, KeyError) as e:
            error_message = f"評価の記録が破損しているか、形式が不正です。詳細: {e}"
            logging.error(error_message)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": error_message}


# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- 戦略立案官ヴェリタス、単独試練の儀を開始 ---")
    strategist = VeritasStrategist()
    proposal = strategist.propose()
    
    print("\n👑 王への進言（Veritas）:")
    # 提案内容を整形して表示
    print(json.dumps(proposal, indent=4, ensure_ascii=False))
    
    logging.info("\n--- 戦略立案官ヴェリタス、単独試練の儀を完了 ---")
