from pydantic import BaseModel

class SystemConfig(BaseModel):
    error_penalty_weight: float = 1.0
    risk_penalty_weight: float = 0.5
    retraining_interval: int = 1000

# グローバル変数として現在の設定を保持（本番ではDBなどが望ましい）
current_config = SystemConfig()
