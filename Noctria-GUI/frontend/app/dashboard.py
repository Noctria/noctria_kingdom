import streamlit as st
import pandas as pd
from strategies.strategy_runner import apply_tradingview_strategy
from execution.risk_control import evaluate_risk
from data.tradingview_fetcher import fetch_tradingview_data

st.title("Noctria GUI - TradingView市場データ統合")

# TradingViewから市場データ取得
raw_data = fetch_tradingview_data()
processed_data = apply_tradingview_strategy(raw_data)

# 市場データの表示
st.subheader("市場データ（TradingView）")
st.dataframe(processed_data)

# 戦略シグナルの表示
st.subheader("戦略シグナル")
st.write(f"現在の戦略: {processed_data['strategy_signal'].iloc[-1]}")

# リスク評価の表示
st.subheader("リスク評価")
st.write(evaluate_risk(processed_data))

# 更新ボタンの追加
if st.button("市場データを更新"):
    raw_data = fetch_tradingview_data()
    processed_data = apply_tradingview_strategy(raw_data)
    st.write("データを更新しました！")
