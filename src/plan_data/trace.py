import os, time, hashlib
from datetime import datetime, timezone

def new_trace_id(symbol: str, timeframe: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rand = hashlib.sha1(f"{now}-{symbol}-{timeframe}-{os.urandom(6)}".encode()).hexdigest()[:8]
    return f"{now}_{symbol}_{timeframe}_{rand}"
