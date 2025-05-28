import streamlit as st
import pandas as pd
import plotly.express as px
import requests

st.title("Noctria GUI 管理・監視ツール")

# サイドバー: 簡単な認証(パスワード: "your_password")
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    password = st.sidebar.text_input("パスワード", type="password")
    if st.sidebar.button("ログイン"):
        if password == "your_password":
            st.session_state['authenticated'] = True
            st.sidebar.success("ログイン成功")
        else:
            st.sidebar.error("パスワードが違います")
else:
    st.sidebar.write("管理者としてログイン中")

# ログ表示セクション
st.subheader("パフォーマンスログ")
try:
    df = pd.read_csv("logs/performance_log.csv")
    fig1 = px.line(df, x="iteration", y="avg_reward", title="平均累積報酬の推移", markers=True)
    st.plotly_chart(fig1, use_container_width=True)
except Exception as e:
    st.error(f"ログの読み込みエラー: {e}")

# 設定変更パネル (認証済のみ)
if st.session_state['authenticated']:
    st.sidebar.header("システム設定")
    new_error_penalty = st.sidebar.slider("Error Penalty Weight", 0.1, 2.0, 1.0, 0.1)
    new_risk_penalty = st.sidebar.slider("Risk Penalty Weight", 0.1, 1.0, 0.5, 0.05)
    new_interval = st.sidebar.number_input("再訓練インターバル (ステップ数)", min_value=500, max_value=2000, value=1000, step=100)
    st.sidebar.write("現在の設定:", new_error_penalty, new_risk_penalty, new_interval)

    if st.sidebar.button("設定を更新"):
        payload = {
            "error_penalty_weight": new_error_penalty,
            "risk_penalty_weight": new_risk_penalty,
            "retraining_interval": new_interval
        }
        try:
            headers = {"x-api-key": "secret-key"}
            response = requests.post("http://localhost:8000/config", json=payload, headers=headers)
            result = response.json()
            st.sidebar.success(f"更新成功: {result['message']}")
            st.sidebar.write("新設定:", result["new_config"])
        except Exception as e:
            st.sidebar.error(f"設定更新に失敗しました: {e}")

# 自動更新 (実験的)
st.experimental_rerun()
