# Noctria Kingdom Airflow Image (v2.6)
# ✅ 修正: ベースイメージをPython 3.11対応のバージョンに変更
FROM apache/airflow:2.9.2-python3.11

# airflowユーザーで以降の処理を実行
USER airflow

# Pythonの依存関係をインストール
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
