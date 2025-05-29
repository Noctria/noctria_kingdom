import streamlit as st
from strategies.strategy_runner import StrategyRunner
from execution.risk_control import evaluate_risk
from data.raw_data_loader import fetch_fintokei_data, optimize_processing

st.title("Noctria GUI - フィントケイ市場データ統合")

# 市場データの表示
processed_df = optimize_processing(fetch_fintokei_data())
st.subheader("市場データ（フィントケイ）")
st.dataframe(processed_df)

# 戦略シグナルの表示
strategy_runner = StrategyRunner(processed_df)
st.subheader("戦略シグナル")
st.write(strategy_runner.run_strategies())

# リスク評価の表示
st.subheader("リスク評価")
st.write(evaluate_risk(processed_df))

# 更新ボタンの追加
if st.button("市場データを更新"):
    processed_df = optimize_processing(fetch_fintokei_data())
    st.write("データを更新しました！")
