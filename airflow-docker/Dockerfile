# ベースイメージに公式の Airflow イメージを使用（バージョンは必要に応じて調整）
FROM apache/airflow:3.0.2-python3.8

# 必要なファイルをコピー
COPY requirements.txt /requirements.txt

# airflowユーザーに切り替えてpip installを実行（rootではエラーになるため）
USER airflow

# Airflow自身と追加ライブラリをインストール
RUN pip install --no-cache-dir apache-airflow==3.0.2 \
    && pip install --no-cache-dir -r /requirements.txt

