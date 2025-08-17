# src/core/decision_hooks.py
# -*- coding: utf-8 -*-
"""
Decision ⇄ Airflow 連携ヘルパ
- DAGトリガ時に Decision を発行し、conf に decision_id を埋めて Airflow を起動。
- 起動結果（dag_run_id / dag_id など）を Decision Registry に追記。

主関数:
create_decision_and_trigger_airflow(
    dag_id: str,
    *,
    kind: str = "act",
    issued_by: str = "ui",
    conf: dict | None = None,
    note: str | None = None,
) -> dict
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from src.core.decision_registry import create_decision, append_event
except Exception as e:  # pragma: no cover
    create_decision = None  # type: ignore
    append_event = None  # type: ignore

try:
    from src.core.airflow_client import make_airflow_client
except Exception as e:  # pragma: no cover
    make_airflow_client = None  # type: ignore


def create_decision_and_trigger_airflow(
    dag_id: str,
    *,
    kind: str = "act",
    issued_by: str = "ui",
    conf: Optional[Dict[str, Any]] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    if create_decision is None or append_event is None:
        raise RuntimeError("Decision Registry が利用できません（src/core/decision_registry.py を確認）")
    if make_airflow_client is None:
        raise RuntimeError("Airflow クライアントが利用できません（src/core/airflow_client.py を確認）")

    # 1) Decision を発行
    decision = create_decision(
        kind=kind,
        issued_by=issued_by,
        intent={"action": "trigger_airflow", "dag_id": dag_id},
        policy_snapshot={},
    )

    # 2) Airflow をトリガ（conf に decision_id を同梱）
    client = make_airflow_client()
    conf_payload = dict(conf or {})
    conf_payload.setdefault("decision_id", decision.decision_id)
    conf_payload.setdefault("issued_by", issued_by)

    run = client.trigger_dag_run(dag_id=dag_id, conf=conf_payload, note=note)

    dag_run_id = str(run.get("dag_run_id") or run.get("dag_run_id".upper()) or "")
    # Airflow のバージョンやプロキシによっては run_id を返すケースもあるためフォールバック
    if not dag_run_id:
        dag_run_id = str(run.get("run_id") or "")

    # 3) レジストリにリンク情報を追記
    append_event(
        decision.decision_id,
        phase="started",
        payload={
            "airflow": {"dag_id": dag_id, "dag_run_id": dag_run_id},
            "conf": conf_payload,
            "note": note or "",
        },
    )

    return {
        "decision": {
            "id": decision.decision_id,
            "kind": decision.kind,
            "issued_by": decision.issued_by,
            "issued_at_utc": decision.issued_at_utc,
        },
        "airflow": {
            "dag_id": dag_id,
            "dag_run_id": dag_run_id,
            "raw": run,
        },
    }
