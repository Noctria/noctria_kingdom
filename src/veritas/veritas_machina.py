# src/veritas/veritas_ai.py

from core.path_config import VERITAS_GENERATE_SCRIPT, VERITAS_EVAL_LOG
from subprocess import run
import json

class VeritasStrategist:
    """
    🧠 Veritas - 自動戦略生成AI（第五の臣下）
    - 戦略生成 → 評価 → 最良の1本を王に提案
    """

    def propose(self) -> dict:
        # 戦略生成（1本）
        run(["python", str(VERITAS_GENERATE_SCRIPT)], check=True)

        # 評価モジュール直接呼び出し（Airflow互換）
        from veritas.evaluate_veritas import evaluate_strategies
        evaluate_strategies()

        # 最良戦略の選定（評価ログを参照）
        with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
            results = json.load(f)

        passed_strategies = [r for r in results if r.get("passed")]
        if not passed_strategies:
            return {"type": "strategy_proposal", "status": "❌ 不採用戦略のみ"}

        best = max(passed_strategies, key=lambda r: r.get("final_capital", 0))
        return {
            "type": "strategy_proposal",
            "strategy": best.get("strategy"),
            "capital": best.get("final_capital"),
            "win_rate": best.get("win_rate"),
            "max_drawdown": best.get("max_drawdown"),
        }

# ✅ 単体テスト
if __name__ == "__main__":
    strategist = VeritasStrategist()
    print("📤 Veritas提案:", strategist.propose())
