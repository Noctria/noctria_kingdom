from fastapi import FastAPI
from app.routes import config_router

app = FastAPI(title="Noctria Backend API")

# APIルートの登録
app.include_router(config_router.router)

# サンプルルート (ヘルスチェック用)
@app.get("/")
async def root():
    return {"message": "Noctria Backend is running"}
