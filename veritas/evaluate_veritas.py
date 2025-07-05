import importlib.util
import pandas as pd
from pathlib import Path
import json
from core.path_config import STRATEGIES_DIR, DATA_DIR, VERITAS_EVAL_LOG

# 📌 評価対象データ
TEST_DATA_PATH = DATA_DIR / "sample_test_data.csv"

# 📌 評価結果ログ格納先
EVAL_LOG_PATH = VERITAS_EVAL_LOG

# ✅ 戦略ファイルを動的に読み込み
def load_strategy(strategy_path: Path):
    module_name = strategy_path.stem
    spec = importlib.util.spec_from_file_location(module_name, strategy_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# ✅ 単一戦略を評価
def evaluate_strategy(strategy_path: Path, test_data: pd.DataFrame):
    strategy_module = load_strategy(strategy_path)
    try:
        result = strategy_module.simulate(test_data)
        return {
            "strategy": strategy_path.name,
            "final_capital": result.get("final_capital", 0),
            "win_rate": result.get("win_rate", 0.0),
            "max_drawdown": result.get("max_drawdown", 1.0),
            "total_trades": result.get("total_trades", 0),
            "passed": (
                result.get("final_capital", 0) > 1_000_000 and
                result.get("win_rate", 0.0) >= 0.5 and
                result.get("max_drawdown", 1.0) <= 0.3
            )
        }
    except Exception as e:
        return {
            "strategy": strategy_path.name,
            "error": str(e),
            "passed": False
        }

# ✅ 全戦略を評価
def evaluate_all_strategies():
    test_data = pd.read_csv(TEST_DATA_PATH)
    results = []

    for path in sorted((STRATEGIES_DIR / "veritas_generated").glob("*.py")):
        result = evaluate_strategy(path, test_data)
        results.append(result)

    return results

# ✅ Airflow対応版 callable（引数なし）
def evaluate_strategies():
    print("⚖️ [Veritas] 戦略評価を開始します…")

    results = evaluate_all_strategies()

    with open(EVAL_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    total = len(results)
    passed = [r for r in results if r.get("passed")]
    print(f"🧠 評価完了: {total} 件の戦略を審査しました。")
    print(f"✅ 採用基準を満たした戦略数: {len(passed)}")
    print("📜 王国訓示:『知を吟味し、未来を選び取る者こそ、王国の盾なり』")

# ✅ スクリプト直接実行時（開発・手動検証用）
if __name__ == "__main__":
    evaluate_strategies()
