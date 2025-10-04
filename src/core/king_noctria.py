# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8
"""
👑 King Noctria (理想型 v4.0) - 五臣による統治 + PM AI (GPT) 兼用版
...
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---- import 経路を安定化 ----
try:
    from src.core.path_config import (
        AIRFLOW_API_BASE,
        ensure_import_path,
        ensure_strategy_packages,
    )
except Exception:
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    SRC_DIR = PROJECT_ROOT / "src"
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    from src.core.path_config import (
        AIRFLOW_API_BASE,
        ensure_import_path,
        ensure_strategy_packages,
    )

ensure_import_path()
ensure_strategy_packages()

# --- ガバナンスYAML → System Prompt 合成
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from src.core.prompt_loader import load_prompt_text, load_governance_dict  # ✅ 修正済み

# -------- 依存のスタブ群 --------
try:
    from src.execution.order_execution import OrderExecution as _OrderExecution
except Exception:
    try:
        from src.do.order_execution import OrderExecution as _OrderExecution
    except Exception:
        _OrderExecution = None

# … (中略: 戦略AIスタブ, _NoopOrderExecution, ロガー定義などは変更なし) …

@dataclass
class CouncilResult:
    decision_id: str
    timestamp: str
    final_decision: str
    raw: Dict[str, Any]

# ------------------- 王 本体 -------------------

class KingNoctria:
    def __init__(self):
        logger.info("王の評議会を構成するため、五臣を招集します。")
        self.veritas = VeritasMachina()
        self.prometheus = PrometheusOracle()
        self.aurus = AurusSingularis()
        self.levia = LeviaTempest()
        self.noctus = NoctusSentinella()
        self.hermes = HermesCognitorStrategy()
        self.order_executor = OrderExecution(api_url="http://host.docker.internal:5001/order")
        logger.info("五臣の招集が完了しました。")
        self._agent_cfg = _load_agent_config()

        # PM AI初期化
        self._gov = None
        self._system_prompt = None
        try:
            self._gov = load_governance_dict()    # ✅ dict 返す
            self._system_prompt = load_prompt_text()  # ✅ 文字列返す
        except Exception as e:
            logger.warning(f"ガバナンスYAML読込に失敗: {e}")
            self._gov = {}
            self._system_prompt = (
                "You are Noctria 王.\n"
                "ROLE: プロジェクトのプロマネ / 最高意思決定者\n"
                "OUTPUT_FORMAT:\n"
                "- Always respond in Japanese.\n"
                "- Return a concise PLAN with numbered steps, plus RISKS and NEXT_ACTIONS.\n"
            )

        self._openai = None
        try:
            self._openai = _get_openai_client()
            logger.info("PM AI クライアントを初期化しました。")
        except Exception as e:
            logger.warning(f"PM AI クライアント初期化に失敗: {e}")

    # decide(), next_actions(), order_trade(), hold_council(), _trigger_dag() は変更なし

# … (以下も大部分はそのまま) …

def _load_agent_config() -> dict:
    import os
    try:
        gov = load_governance_dict()   # ✅ dictで読み込む
    except Exception:
        return {}
    agent = gov.get("agent", {}) or {}
    tools = gov.get("tools", {}) or {}
    automations = gov.get("automations", {}) or {}
    routing = gov.get("routing", {}) or {}
    memory_policy = gov.get("memory_policy", {}) or {}
    if os.getenv("NOCTRIA_AGENT_ENABLE"):
        agent["enabled"] = os.getenv("NOCTRIA_AGENT_ENABLE") == "1"
    if os.getenv("NOCTRIA_AGENT_MAX_STEPS"):
        agent["max_steps"] = int(os.getenv("NOCTRIA_AGENT_MAX_STEPS"))
    return {
        "agent": agent,
        "tools": tools,
        "automations": automations,
        "routing": routing,
        "memory_policy": memory_policy,
    }

# (残りの _agent_memory_append, _agent_postprocess などは変更なし)
