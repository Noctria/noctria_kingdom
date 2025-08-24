# src/plan_data/__init__.py の末尾あたりに追記
try:
    from .trace import new_trace_id, get_trace_id, set_trace_id, bind_trace_id
except Exception:
    pass

