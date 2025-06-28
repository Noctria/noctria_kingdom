import importlib.util
import os
import pandas as pd
from typing import Dict

def simulate_strategy_adjusted(path: str, market_data: pd.DataFrame) -> Dict:
    """
    戦略ファイル (.py) を動的に読み込み simulate(market_data) を実行し、
    評価メトリクス（dict形式）を返す。

    必須: simulate() が dict を返し、"final_capital" キーを含むこと。

    :param path: 戦略ファイルのフルパス
    :param market_data: 評価用の市場データ（DataFrame）
    :return: 評価結果（dict）
    """
    result = {
        "final_capital": None,
        "win_rate": None,
        "max_drawdown": None,
        "total_trades": None,
        "status": "error",
        "error_message": None,
        "filename": os.path.basename(path)
    }

    if not os.path.exists(path):
        result["error_message"] = f"ファイルが存在しません: {path}"
        return result

    module_name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        result["error_message"] = f"モジュールの読み込みに失敗: {e}"
        return result

    if not hasattr(module, "simulate"):
        result["error_message"] = f"simulate() 関数が {path} に定義されていません"
        return result

    try:
        sim_output = module.simulate(market_data)

        if not isinstance(sim_output, dict):
            result["error_message"] = f"simulate() の戻り値が dict ではありません: {type(sim_output)}"
            return result

        if "final_capital" not in sim_output:
            result["error_message"] = "simulate() の戻り値に 'final_capital' が存在しません"
            return result

        result.update(sim_output)
        result["status"] = "ok"

    except Exception as e:
        result["error_message"] = f"simulate() 実行エラー: {e}"

    return result
