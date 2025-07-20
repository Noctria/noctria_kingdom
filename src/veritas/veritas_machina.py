#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas Strategist (v2.5)
- ベスト戦略の根拠説明つき
- 生成/評価の標準出力・エラーをファイル保存
- パラメータ柔軟渡し＆ランキング返却
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

    def _build_cli_args(self, param_dict: Dict[str, Any]) -> List[str]:
        args = []
        for k, v in param_dict.items():
            args.append(f"--{k}")
            if isinstance(v, bool):
                v = str(v).lower()
            args.append(str(v))
        return args

    def _make_explanation(self, best: dict, rankings: List[dict]) -> str:
        """最良戦略の根拠を動的に生成"""
        try:
            avg_win = sum(r.get("win_rate", 0) for r in rankings) / len(rankings) if rankings else 0
            avg_dd = sum(r.get("max_drawdown", 0) for r in rankings) / len(rankings) if rankings else 0
            # シャープレシオ（仮）なども比較
            best_wr = best.get("win_rate", None)
            best_dd = best.get("max_drawdown", None)
            best_sharpe = best.get("sharpe_ratio", None)
            lines = []
            if best_wr is not None:
                lines.append(f"勝率: {best_wr:.2f}%（合格戦略平均: {avg_win:.2f}%）")
            if best_dd is not None:
                lines.append(f"最大DD: {best_dd:.2f}（合格戦略平均: {avg_dd:.2f}）")
            if best_sharpe is not None:
                lines.append(f"シャープレシオ: {best_sharpe:.3f}")
            base_reason = "final_capital最大かつ安定性・勝率等で最良だったため選定"
            lines.append(base_reason)
            return " / ".join(lines)
        except Exception as e:
            return f"自動説明生成エラー: {e}"

    def propose(self, top_n: int = 5, **params) -> Dict[str, Any]:
        # 1. 戦略生成
        try:
            logging.info(f"新たな戦略の創出を開始します…（パラメータ: {params}）")
            cli_args = self._build_cli_args(params)
            res = subprocess.run(
                ["python", str(VERITAS_GENERATE_SCRIPT)] + cli_args,
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
            logging.info(f"生成された戦略の評価の儀を開始します…（パラメータ: {params}）")
            cli_args = self._build_cli_args(params)
            res = subprocess.run(
                ["python", str(VERITAS_EVALUATE_SCRIPT)] + cli_args,
                check=True, capture_output=True, text=True
            )
            self._save_subprocess_output(res, self.evaluate_log_path, "VERITAS EVALUATE")
            logging.info("評価の儀が完了しました。")
        except subprocess.CalledProcessError as e:
            self._save_subprocess_output(e, self.evaluate_log_path, "VERITAS EVALUATE (FAILED)")
            error_message = f"戦略評価の儀で失敗しました。詳細: {e.stderr or e}"
            logging.error(error_message)
            return {"type": "strategy_proposal", "status": "ERROR", "detail": error_message}

        # 3. 最良戦略とランキング返却（説明つき）
        try:
            logging.info("評価結果から最良戦略とランキングを選定します…")
            with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
                results = json.load(f)
            passed_strategies = [r for r in results if r.get("passed")]
            if not passed_strategies:
                msg = "全ての戦略が評価基準を満たしませんでした。"
                logging.warning(msg)
                return {"type": "strategy_proposal", "status": "REJECTED", "detail": msg, "strategy_rankings": []}
            rankings: List[dict] = sorted(
                passed_strategies,
                key=lambda r: r.get("final_capital", 0),
                reverse=True
            )[:top_n]
            best_strategy = rankings[0]
            explanation = self._make_explanation(best_strategy, rankings)
            logging.info(f"最良の戦略『{best_strategy.get('strategy')}』を選定。根拠: {explanation}")
            return {
                "name": "Veritas",
                "type": "strategy_proposal",
                "status": "PROPOSED",
                "strategy_details": best_strategy,
                "strategy_rankings": rankings,
                "explanation": explanation,
                "params": params
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
    proposal = strategist.propose(top_n=5, risk=0.01, symbol="USDJPY", lookback=180)
    print("\n👑 王への進言（Veritas）:")
    print(json.dumps(proposal, indent=4, ensure_ascii=False))
    logging.info("\n--- 戦略立案官ヴェリタス、単独試練の儀を完了 ---")
