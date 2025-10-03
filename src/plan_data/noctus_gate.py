from src.execution.order_execution import OrderExecution
from src.plan_data.noctus_gate import gate_and_prepare_order

gate = gate_and_prepare_order(
    noctus_result,  # NoctusSentinella.calculate_lot_and_risk の結果
    symbol="USDJPY",
    side="BUY",
    entry_price=152.60,
    stop_loss=152.30,
    decision_id=noctus_result.get("decision_id"),
    caller="king_noctria",
    reason="from council",
)

if gate.ok and gate.normalized:
    exe = OrderExecution(api_url="http://host.docker.internal:5001/order", dry_run=True)
    r = exe.execute_order(**gate.normalized)
    print(r)
else:
    print("blocked:", gate.reasons)
