# test_data_preprocessing.py

import pytest
import pandas as pd
from data_preprocessing import load_data, preprocess_data

def test_load_data_with_valid_file(tmp_path):
    # 一時的なCSVファイルを生成
    file = tmp_path / "data.csv"
    file.write_text("a,b\n1,2\n3,4")
    df = load_data(str(file))
    assert not df.empty

def test_load_data_with_missing_file():
    df = load_data("not_exist.csv")
    assert df.empty

def test_preprocess_data_fillna():
    df = pd.DataFrame({"a": [1, None], "b": [3, 4]})
    result = preprocess_data(df)
    assert result.isna().sum().sum() == 0
