from fastapi import APIRouter, HTTPException, Header, Depends
from app.config import SystemConfig, current_config

router = APIRouter()

# 簡単な API キー認証の例
API_KEY = "secret-key"

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/config", response_model=SystemConfig)
async def get_config():
    return current_config

@router.post("/config", dependencies=[Depends(verify_api_key)])
async def update_config(new_config: SystemConfig):
    global current_config
    current_config = new_config
    return {"message": "設定が更新されました", "new_config": current_config}
