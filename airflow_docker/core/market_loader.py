# /noctria_kingdom/core/market_loader.py

import pandas as pd

def load_market_data(file_path: str) -> pd.DataFrame:
    return pd.read_csv(file_path)
