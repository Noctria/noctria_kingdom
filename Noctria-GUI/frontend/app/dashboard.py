#!/usr/bin/env python3
# coding: utf-8

import streamlit as st
import pandas as pd
from strategies.strategy_runner import apply_tradingview_strategy
from execution.risk_control import evaluate_risk
from data.tradingview_fetcher import fetch_tradingview_data

st.set_page_config(page_title="Noctria GUI - TradingView市場データ", layout="wide")
st.title("📈 Noctria GUI - TradingView市場データ統合")

# 初期データをセッションに保持
if "processed_data" not in st.session_state:
    try:
        raw_data = fetch_tradingview_data()
        processed_data = apply_tradingview_strategy(raw_data)
        st.session_state["processed_data"] = processed_data
        st.session_state["last_update"] = pd.Timestamp.now()
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        st.stop()

# 更新ボタン
if st.button("🔄 市場データを更新"):
    try:
        raw_data = fetch_tradingview_data()
        processed_data = apply_tradingview_strategy(raw_data)
        st.session_state["processed_data"] = processed_data
        st.session_state["last_update"] = pd.Timestamp.now()
        st.success("✅ データを更新しました！")
    except Exception as e:
        st.error(f"更新時にエラーが発生しました: {e}")

# データ表示
data = st.session_state.get("processed_data", pd.DataFrame())
if not data.empty:
    st.caption(f"🕒 最終更新: {st.session_state['last_update'].strftime('%Y-%m-%d %H:%M:%S')}")
    st.subheader("🗃 市場データ（TradingView）")
    st.dataframe(data, use_container_width=True)

    # 戦略シグナル表示
    st.subheader("📊 戦略シグナル")
    try:
        signal = data['strategy_signal'].iloc[-1]
        st.write(f"現在の戦略: **{signal}**")
    except Exception:
        st.warning("戦略シグナル情報が見つかりませんでした。")

    # リスク評価表示
    st.subheader("🧠 リスク評価")
    try:
        risk_result = evaluate_risk(data)
        st.json(risk_result)
    except Exception as e:
        st.error(f"リスク評価エラー: {e}")
else:
    st.warning("市場データが空です。")
