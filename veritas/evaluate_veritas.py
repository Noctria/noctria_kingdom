import importlib.util
import pandas as pd
from core.path_config import STRATEGIES_DIR, DATA_DIR
import os

# ✅ テストデータの読み込み（M1価格など）
TEST_DATA_PATH = DATA_DIR / "sample_test_data.csv"  # 仮ファイル名
TEST_DATA = pd.read_csv(TEST_DATA_PATH)

# ✅ 評価基準
MIN_WIN_RATE = 0.55
MAX_DRAWDOWN = 0.2
MIN_TRADES = 5

def evaluate_strategy(file_path):
    # 戦略モジュールを動的にロード
    spec = importlib.util.spec_from_file_location("strategy", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # simulate 実行
    result = module.simulate(TEST_DATA)

    # 評価基準との比較
    passed = (
        result["win_rate"] >= MIN_WIN_RATE and
        result["max_drawdown"] <= MAX_DRAWDOWN and
        result["total_trades"] >= MIN_TRADES
    )

    return {
        "file": os.path.basename(file_path),
        "result": result,
        "passed": passed
    }

def evaluate_all_strategies():
    strategy_files = sorted(STRATEGIES_DIR.glob("veritas_generated/*.py"))
    results = []

    for f in strategy_files:
        try:
            res = evaluate_strategy(str(f))
            results.append(res)
        except Exception as e:
            results.append({
                "file": str(f),
                "error": str(e),
                "passed": False
            })

    return results

if __name__ == "__main__":
    evaluations = evaluate_all_strategies()
    for ev in evaluations:
        print("🧪", ev["file"])
        print("   ✅ Passed:", ev["passed"])
        print("   📊 Result:", ev.get("result", ev.get("error")))
