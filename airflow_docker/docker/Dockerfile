FROM apache/airflow:2.9.2-python3.11

USER root
RUN apt-get update && apt-get install -y git

USER airflow

COPY requirements_extra.txt /requirements_extra.txt

# 依存関係インストール
RUN pip install --no-cache-dir -r /requirements_extra.txt

# sb3-contribは明示的にGitHubから（安定してればPyPI版でもOK）
RUN pip install --no-cache-dir git+https://github.com/Stable-Baselines-Team/stable-baselines3-contrib.git@v2.2.1
