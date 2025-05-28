FROM python:3.9-slim

WORKDIR /app

# 依存パッケージのコピーとインストール
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
COPY . .

EXPOSE 8000

# FastAPI アプリを uvicorn で起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
