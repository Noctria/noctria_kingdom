from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from strategies.prometheus_oracle import PrometheusOracle

router = APIRouter(prefix="/prometheus", tags=["PrometheusOracle"])

@router.get("/predict")
async def predict(
    n_days: int = Query(14, ge=1, le=60),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
):
    try:
        oracle = PrometheusOracle()
        df = oracle.predict_with_confidence(n_days=n_days, from_date=from_date, to_date=to_date)
        records = df.to_dict(orient="records")
        return JSONResponse(content={"predictions": records})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in prediction: {e}")
