from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from strategies.prometheus_oracle import PrometheusOracle
import logging

router = APIRouter(prefix="/prometheus", tags=["PrometheusOracle"])

logger = logging.getLogger("prometheus_routes")

@router.get("/predict")
async def predict(
    n_days: int = Query(14, ge=1, le=60, description="予測日数（1～60日）"),
    from_date: Optional[str] = Query(None, description="予測開始日（YYYY-MM-DD形式）"),
    to_date: Optional[str] = Query(None, description="予測終了日（YYYY-MM-DD形式）"),
):
    """
    PrometheusOracleによる信頼区間付き市場予測API
    """
    try:
        oracle = PrometheusOracle()
        df = oracle.predict_with_confidence(n_days=n_days, from_date=from_date, to_date=to_date)
        records = df.to_dict(orient="records")
        return JSONResponse(content={"predictions": records})
    except Exception as e:
        logger.error(f"Error in PrometheusOracle prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in prediction: {e}")
