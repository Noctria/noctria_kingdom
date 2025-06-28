FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# FastAPI + 依存関係インストール
COPY ./app /app/app
COPY requirements.txt /app

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ポート開放
EXPOSE 8000

# 起動コマンド
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
