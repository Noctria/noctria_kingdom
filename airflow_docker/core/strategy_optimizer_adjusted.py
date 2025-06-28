import importlib.util
import os
import pandas as pd
from typing import Optional

def simulate_strategy_adjusted(path: str, market_data: pd.DataFrame) -> Optional[float]:
    """
    指定された戦略ファイル (.py) を動的に読み込み simulate(market_data) を実行し、
    最終資産（float）を返す。
    
    :param path: 戦略ファイルのフルパス
    :param market_data: 評価用の市場データ（DataFrame）
    :return: 評価結果（float）または None
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ ファイルが存在しません: {path}")

    module_name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise RuntimeError(f"⚠️ モジュールの読み込みに失敗しました: {e}")

    if not hasattr(module, "simulate"):
        raise AttributeError(f"❌ simulate() 関数が {path} に定義されていません")

    try:
        result = module.simulate(market_data)
    except Exception as e:
        raise RuntimeError(f"⚠️ simulate() 実行時にエラー: {e}")

    if not isinstance(result, (int, float)):
        raise ValueError(f"❌ simulate() の戻り値が数値型ではありません: {type(result)}")

    return float(result)
