FROM apache/airflow:2.9.2-python3.11

# git を入れるためにrootで実行
USER root
RUN apt-get update && apt-get install -y git

# airflowユーザーに戻す
USER airflow

# 依存パッケージをコピーしてインストール
COPY requirements_extra.txt /requirements_extra.txt

# requirements_extra.txtをインストール後、追加でGitHubからsb3-contribをインストール
RUN pip install --no-cache-dir -r /requirements_extra.txt \
    && pip install --no-cache-dir git+https://github.com/Stable-Baselines-Team/stable-baselines3-contrib.git@v2.2.1
