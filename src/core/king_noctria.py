# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8

"""
👑 King Noctria (理想型 v4.0) - 五臣による統治 + PM AI (GPT) 兼用版

既存機能:
- decision_id, caller, reason で統治判断を一元管理
- 全DAG/AI/臣下呼び出し・御前会議・トリガーで decision_id を必ず発行・伝搬
- 統治履歴は全て decision_id 単位で JSON ログ保存
- Do層 order_execution.py をリスクガード・SL強制付きで一元制御
- ロット/リスク計算は Noctus（NoctusSentinella）へ委譲
- import 経路を統一（src. で統一）しつつ、依存が未実装でも落ちない最小スタブを同梱

追加機能（本コミット）:
- PM AI: docs/governance/king_ops_prompt.yaml (+ !include 群) を読み込み、
  System Prompt を合成 → GPT API にコンテキストを渡して意思決定を取得する decide() を実装
- NEXT_ACTIONS を配列で抽出するユーティリティを実装
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

# ---- import 経路を安定化（src パスを追加 & strategies の __init__.py を保証）----
try:
    from src.core.path_config import (
        AIRFLOW_API_BASE,
        ensure_import_path,
        ensure_strategy_packages,
    )
except Exception:
    # 直起動で src が通っていない場合の保険
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    SRC_DIR = PROJECT_ROOT / "src"
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    # 再トライ
    from src.core.path_config import (
        AIRFLOW_API_BASE,
        ensure_import_path,
        ensure_strategy_packages,
    )

# src 直下 import を有効化
ensure_import_path()
# strategies パッケージの __init__.py を自動整備（足りなければ最小生成）
ensure_strategy_packages()

# --- ガバナンスYAML → System Prompt 合成
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from src.core.prompt_loader import load_governance, render_system_prompt  # noqa: E402

# -------- 依存（存在しない場合に備えて安全スタブ化） -----------------

# Do層（order execution）
try:
    from src.execution.order_execution import OrderExecution as _OrderExecution  # 旧構成
except Exception:
    try:
        from src.do.order_execution import OrderExecution as _OrderExecution  # 新構成（将来）
    except Exception:
        _OrderExecution = None  # 後で Noop に置換


# 戦略/臣下AI
def _safe_import(default_cls_name: str, import_path: str, fallback_doc: str):
    """
    import 失敗時でも落とさずに動く最小スタブクラスを返す。
    """
    try:
        module_path, cls_name = import_path.rsplit(".", 1)
        mod = __import__(module_path, fromlist=[cls_name])
        return getattr(mod, cls_name)
    except Exception:

        class _Fallback:
            __name__ = default_cls_name

            def __init__(self, *args, **kwargs):
                logging.getLogger("king_noctria").warning(
                    f"[stub] {default_cls_name} is missing ({import_path}); using fallback."
                )

            # 最低限のインタフェース
            def propose(self, *args, **kwargs) -> Dict[str, Any]:
                return {"signal": "HOLD", "reason": "fallback_stub"}

            def predict(self, *args, **kwargs) -> Dict[str, Any]:
                return {"forecast": "neutral", "detail": "fallback_stub"}

            def assess(self, *args, **kwargs) -> Dict[str, Any]:
                return {"decision": "APPROVE", "reason": "fallback_stub"}

            # NoctusSentinella 向け
            def calculate_lot_and_risk(self, *args, **kwargs) -> Dict[str, Any]:
                return {
                    "decision": "APPROVE",
                    "lot": 0.01,
                    "reason": "fallback_stub",
                    "decision_id": kwargs.get("decision_id"),
                }

        _Fallback.__doc__ = fallback_doc
        return _Fallback


AurusSingularis = _safe_import(
    "AurusSingularis",
    "src.strategies.aurus_singularis.AurusSingularis",
    "市場トレンド解析のスタブ",
)
LeviaTempest = _safe_import(
    "LeviaTempest",
    "src.strategies.levia_tempest.LeviaTempest",
    "高速スキャルピングAIのスタブ",
)
NoctusSentinella = _safe_import(
    "NoctusSentinella",
    "src.strategies.noctus_sentinella.NoctusSentinella",
    "リスク管理AIのスタブ",
)
PrometheusOracle = _safe_import(
    "PrometheusOracle",
    "src.strategies.prometheus_oracle.PrometheusOracle",
    "中長期予測AIのスタブ",
)
HermesCognitorStrategy = _safe_import(
    "HermesCognitorStrategy",
    "src.strategies.hermes_cognitor.HermesCognitorStrategy",
    "戦略説明AIのスタブ",
)
VeritasMachina = _safe_import(
    "VeritasMachina",
    "src.veritas.veritas_machina.VeritasMachina",
    "戦略最適化/検証のスタブ",
)


# OrderExecution の No-Op 代替
class _NoopOrderExecution:
    def __init__(self, api_url: str = "http://localhost:5001/order"):
        self.api_url = api_url
        logging.getLogger("king_noctria").warning(
            "[stub] OrderExecution missing; using No-Op executor."
        )

    def execute_order(
        self,
        *,
        symbol: str,
        lot: float,
        order_type: str,
        entry_price: float,
        stop_loss: float,
    ) -> Dict[str, Any]:
        return {
            "status": "noop",
            "symbol": symbol,
            "lot": lot,
            "order_type": order_type,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "note": "OrderExecution not available (No-Op).",
        }


OrderExecution = _OrderExecution or _NoopOrderExecution

# -------------- ロガー --------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - 👑 KingNoctria: %(message)s",
)
logger = logging.getLogger("king_noctria")

from pathlib import Path as _Path

_PROJECT_ROOT = _Path(__file__).resolve().parents[2]
KING_LOG_PATH = os.getenv(
    "KING_LOG_PATH", str((_PROJECT_ROOT / "data" / "king_decision_log.json").resolve())
)


def _generate_decision_id(prefix: str = "KC") -> str:
    dt = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{dt}-{unique}"


def _save_king_log(entry: dict) -> None:
    try:
        # 先にディレクトリを保証
        from pathlib import Path

        Path(KING_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(KING_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"King log保存失敗: {e}")


@dataclass
class CouncilResult:
    decision_id: str
    timestamp: str
    final_decision: str
    raw: Dict[str, Any]


# ------------------- PM AI（GPT）ユーティリティ -------------------


def _get_openai_client():
    """OpenAI v1 クライアント（互換エンドポイント可）を初期化。"""
    try:
        from openai import OpenAI  # OpenAI Python v1 系
    except Exception as e:
        raise RuntimeError(
            "openai パッケージが見つかりません。`pip install openai>=1.40.0` を実行してください。"
        ) from e

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が未設定です（.env か環境変数に設定してください）。")

    base = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
    if base:
        return OpenAI(api_key=api_key, base_url=base)
    return OpenAI(api_key=api_key)


DEFAULT_MODEL = os.getenv("NOCTRIA_GPT_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"


def _extract_json_block(text: str) -> Dict[str, Any]:
    """
    回答文中の ```json ... ``` ブロックから JSON を抽出（任意）。
    失敗時は {} を返す。
    """
    try:
        m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if m:
            return json.loads(m.group(1))
    except Exception:
        pass
    return {}


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

        # PM AI（GPT）初期化（必要時に遅延初期化でも良いが、ここでしておく）
        self._gov = None
        self._system_prompt = None
        try:
            self._gov = (
                load_governance()
            )  # docs/governance/king_ops_prompt.yaml (+ !include) を統合
            self._system_prompt = render_system_prompt(self._gov)
        except Exception as e:
            logger.warning(f"ガバナンスYAML読込に失敗しました（PM AIは制限モードで動作）: {e}")
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
            logger.warning(f"PM AI クライアント初期化に失敗（OPENAI_API_KEY などを確認）: {e}")

    # --- PM AI: ガバナンスに基づく意思決定 ---
    def decide(
        self,
        context: Dict[str, Any],
        instructions: Optional[str] = None,
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        プロマネとしての王の意思決定を取得。
        context: 進捗/課題/メトリクスなどの辞書（JSON相当）
        instructions: 今回の判断テーマ（任意）
        戻り値: {"raw": str, "parsed": {...}, "model": str}
        """
        if self._openai is None:
            raise RuntimeError(
                "PM AI クライアントが未初期化です。OPENAI_API_KEY 等を確認してください。"
            )

        sys_prompt = self._system_prompt or "You are Noctria 王. Always respond in Japanese."
        user_msg = (
            "以下はNoctria王国プロジェクトの状況です。\n"
            f"CONTEXT_JSON:\n```json\n{json.dumps(context, ensure_ascii=False, indent=2)}\n```\n"
        )
        if instructions:
            user_msg += f"\nSPECIAL_INSTRUCTIONS:\n{instructions}\n"

        resp = self._openai.chat.completions.create(
            model=(model or DEFAULT_MODEL),
            temperature=temperature,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_msg},
            ],
        )
        text = resp.choices[0].message.content or ""
        parsed = _extract_json_block(text)

        # 決定のトレースを保存（軽量）
        try:
            _save_king_log(
                {
                    "timestamp": datetime.now().isoformat(),
                    "decision_id": _generate_decision_id("PM"),
                    "type": "pm_decide",
                    "context": context,
                    "instructions": instructions,
                    "model": model or DEFAULT_MODEL,
                    "raw": text[:2000],  # ログ肥大化防止
                    "parsed_keys": list(parsed.keys()),
                }
            )
        except Exception:
            pass

        return {"raw": text, "parsed": parsed, "model": (model or DEFAULT_MODEL)}

    def next_actions(self, decision: Dict[str, Any]) -> List[str]:
        """
        decide() の戻り値から次アクションをしぶとく抽出して配列で返す。
        優先度:
          1) JSONの正式キー: NEXT_ACTIONS / next_actions
          2) JSONの別名キー: action(s) / todo(s) / task(s)
          3) RAW本文の "NEXT_ACTIONS" セクション配下の箇条書き or 1. 行
          4) RAW本文全体の箇条書き (フォールバック)
        """
        p = (decision or {}).get("parsed") or {}
        raw = (decision or {}).get("raw") or ""

        # 1) 正式キー
        xs = p.get("NEXT_ACTIONS") or p.get("next_actions")
        if isinstance(xs, str) and xs.strip():
            return [xs.strip()]
        if isinstance(xs, list) and xs:
            return [str(i).strip() for i in xs if str(i).strip()]

        # 2) 別名キー（単数/複数）
        for k in ["action", "actions", "todo", "todos", "task", "tasks"]:
            v = p.get(k)
            if isinstance(v, str) and v.strip():
                return [v.strip()]
            if isinstance(v, list) and v:
                return [str(i).strip() for i in v if str(i).strip()]

        # 3) "NEXT_ACTIONS" セクション狙い撃ち
        try:
            import re as _re

            m = _re.search(r"(?mi)^(?:#{1,6}\s*)?NEXT[_\s-]*ACTIONS\s*:?\s*$", raw)
            if m:
                tail = raw[m.end() :]
                cut = _re.split(r"(?m)^(?:#{1,6}\s+|\Z)", tail, maxsplit=1)[0]
                bullets = _re.findall(r"(?m)^\s*(?:[-・*]\s+)(.+)$", cut)
                numbered = _re.findall(r"(?m)^\s*\d+[.)]\s+(.+)$", cut)
                items = [i.strip() for i in (bullets + numbered) if i.strip()]
                if items:
                    return items[:10]
                jm = _re.search(r"```json\s*(\{.*?\})\s*```", cut, _re.DOTALL)
                if jm:
                    import json as _json

                    try:
                        jd = _json.loads(jm.group(1))
                        for k in [
                            "NEXT_ACTIONS",
                            "next_actions",
                            "action",
                            "actions",
                            "todo",
                            "todos",
                            "task",
                            "tasks",
                        ]:
                            v = jd.get(k)
                            if isinstance(v, str) and v.strip():
                                return [v.strip()]
                            if isinstance(v, list) and v:
                                return [str(i).strip() for i in v if str(i).strip()]
                    except Exception:
                        pass
        except Exception:
            pass

        # 4) 全文フォールバック
        return _heuristic_extract_next_actions(raw)

    def order_trade(
        self,
        *,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss_price: float,
        capital: float,
        risk_percent: float = 0.01,
        feature_dict: Optional[dict] = None,
        caller: str = "king_noctria",
        reason: str = "AI指令自動注文",
    ) -> Dict[str, Any]:
        """
        王命による安全発注メソッド。ロット計算とリスク許可判定は Noctus に委譲。
        """
        # 1) ロット/リスク判定を Noctus に依頼
        if feature_dict is None:
            feature_dict = {
                "price": entry_price,
                "volume": 100,
                "spread": 0.01,
                "volatility": 0.15,
                "historical_data": pd.DataFrame({"Close": np.random.normal(entry_price, 2, 100)}),
            }

        decision_id = _generate_decision_id()
        noctus_result = self.noctus.calculate_lot_and_risk(
            feature_dict=feature_dict,
            side=side,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            capital=capital,
            risk_percent=risk_percent,
            decision_id=decision_id,
            caller=caller,
            reason=reason,
        )

        if noctus_result.get("decision") != "APPROVE":
            _save_king_log(
                {
                    "timestamp": datetime.now().isoformat(),
                    "decision_id": noctus_result.get("decision_id", decision_id),
                    "caller": caller,
                    "reason": reason,
                    "symbol": symbol,
                    "side": side,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss_price,
                    "capital": capital,
                    "risk_percent": risk_percent,
                    "noctus_result": noctus_result,
                    "status": "REJECTED",
                }
            )
            return {"status": "rejected", "noctus_result": noctus_result}

        lot = float(noctus_result.get("lot", 0.0))
        # 2) Do層API発注（SL必須）
        result = self.order_executor.execute_order(
            symbol=symbol,
            lot=lot,
            order_type=side,
            entry_price=entry_price,
            stop_loss=stop_loss_price,
        )
        # 3) 王の決裁ログ記録
        order_log = {
            "timestamp": datetime.now().isoformat(),
            "decision_id": noctus_result.get("decision_id", decision_id),
            "caller": caller,
            "reason": reason,
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "stop_loss": stop_loss_price,
            "lot": lot,
            "capital": capital,
            "risk_percent": risk_percent,
            "noctus_result": noctus_result,
            "api_result": result,
            "status": "EXECUTED"
            if result.get("status") not in {"error", "noop"}
            else result.get("status"),
        }
        _save_king_log(order_log)
        return result

    def hold_council(
        self, market_data: dict, *, caller="king_routes", reason="御前会議決裁"
    ) -> CouncilResult:
        decision_id = _generate_decision_id()
        timestamp = datetime.now().isoformat()
        logger.info(f"--------------------\n📣 御前会議を開催（decision_id={decision_id}）…")

        # 臣下AIの報告収集
        aurus_proposal = self.aurus.propose(market_data)
        levia_proposal = self.levia.propose(market_data)
        prometheus_forecast = self.prometheus.predict(n_days=7)
        hermes_explanation = self.hermes.propose(
            {
                "features": market_data,
                "labels": [
                    "Aurus: " + str(aurus_proposal.get("signal", "")),
                    "Levia: " + str(levia_proposal.get("signal", "")),
                ],
                "reason": reason,
            }
        )

        # 決定プロセス
        primary_action = aurus_proposal.get("signal")
        if primary_action == "HOLD":
            logger.info("Aurusは静観を推奨。Leviaの短期的な見解を求めます。")
            primary_action = levia_proposal.get("signal")
        logger.info(f"主たる進言は『{primary_action}』と決定しました。")

        noctus_assessment = self.noctus.assess(market_data, primary_action)
        final_decision = primary_action
        if noctus_assessment.get("decision") == "VETO":
            logger.warning(f"Noctusが拒否権を発動！理由: {noctus_assessment.get('reason')}")
            logger.warning("安全を最優先し、最終判断を『HOLD』に変更します。")
            final_decision = "HOLD"
        else:
            logger.info("Noctusは行動を承認。進言通りに最終判断を下します。")
        logger.info(f"👑 下される王命: 『{final_decision}』\n--------------------")

        report = {
            "decision_id": decision_id,
            "timestamp": timestamp,
            "caller": caller,
            "reason": reason,
            "final_decision": final_decision,
            "assessments": {
                "aurus_proposal": aurus_proposal,
                "levia_proposal": levia_proposal,
                "noctus_assessment": noctus_assessment,
                "prometheus_forecast": prometheus_forecast,
                "hermes_explanation": hermes_explanation,
            },
        }
        _save_king_log(report)
        return CouncilResult(
            decision_id=decision_id, timestamp=timestamp, final_decision=final_decision, raw=report
        )

    def _trigger_dag(
        self,
        dag_id: str,
        conf: Optional[Dict[str, Any]] = None,
        airflow_user: str = "admin",
        airflow_pw: str = "admin",
        *,
        caller="king_noctria",
        reason="王命トリガー",
    ) -> Dict[str, Any]:
        """
        Airflow DAG を API 経由で起動。成功/失敗ともに king_log に記録。
        """
        decision_id = _generate_decision_id()
        payload_conf = dict(conf or {})
        payload_conf.update(
            {
                "decision_id": decision_id,
                "caller": caller,
                "reason": reason,
            }
        )
        endpoint = f"{AIRFLOW_API_BASE}/api/v1/dags/{dag_id}/dagRuns"
        auth = (airflow_user, airflow_pw)
        timestamp = datetime.now().isoformat()
        try:
            resp = requests.post(endpoint, json={"conf": payload_conf}, auth=auth, timeout=10)
            resp.raise_for_status()
            result = {"status": "success", "result": resp.json()}
            log_entry = {
                "decision_id": decision_id,
                "timestamp": timestamp,
                "dag_id": dag_id,
                "trigger_conf": payload_conf,
                "caller": caller,
                "reason": reason,
                "trigger_type": "dag",
                "status": "success",
                "result": resp.json(),
            }
            _save_king_log(log_entry)
            return result
        except Exception as e:
            log_entry = {
                "decision_id": decision_id,
                "timestamp": timestamp,
                "dag_id": dag_id,
                "trigger_conf": payload_conf,
                "caller": caller,
                "reason": reason,
                "trigger_type": "dag",
                "status": "error",
                "error": str(e),
            }
            _save_king_log(log_entry)
            logger.error(f"Airflow DAG [{dag_id}] トリガー失敗: {e}")
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    logger.info("--- 王の中枢機能、単独試練の儀を開始 ---")
    king = KingNoctria()

    # 1) PM AI としての意思決定（.env が正しく設定されていれば応答あり）
    try:
        decision = king.decide(
            context={
                "ci": {
                    "runner": "wsl2",
                    "status": "connected",
                    "issues": ["pytest-heavy", "deps-missing"],
                }
            },
            instructions="本日(Asia/Tokyo)の最小到達計画・リスク・次アクションを短く提示して。コマンドも1-2行だけ。",
        )
        print("=== PM DECISION RAW ===")
        print(decision["raw"])
        print("=== NEXT ACTIONS ===")
        print(king.next_actions(decision))
    except Exception as e:
        logger.warning(f"PM decide スキップ: {e}")

    # 2) 公式発注ラッパ（OrderExecution が無い場合は No-Op）
    result = king.order_trade(
        symbol="USDJPY",
        side="buy",
        entry_price=157.20,
        stop_loss_price=156.70,
        capital=20000,  # 現口座資金
        risk_percent=0.007,  # 0.7%など
        caller="AIシナリオ",
        reason="AI推奨取引",
    )
    print("公式発注結果:", result)
    logger.info("--- 王の中枢機能、単独試練の儀を完了 ---")


def _heuristic_extract_next_actions(text: str) -> list[str]:
    """
    JSON/キー名の揺れでパースできない時のフォールバック抽出。
    - 「NEXT ACTIONS/次アクション」節の箇条書き・番号行を優先抽出
    - 全文からの箇条書き抽出
    - セクション内の ```json { ... } ``` があれば広めのキーで拾う
    """
    import json
    import re

    if not text:
        return []
    items: list[str] = []

    # 1) セクション狙い撃ち
    try:
        m = re.search(r"(?mi)^(?:#{1,6}\s*)?NEXT[_\s-]*ACTIONS\s*:?\s*$", text)
        if m:
            tail = text[m.end() :]
            cut = re.split(r"(?m)^(?:#{1,6}\s+|\Z)", tail, maxsplit=1)[0]
            bullets = re.findall(r"(?m)^\s*(?:[-・*]\s+)(.+)$", cut)
            numbered = re.findall(r"(?m)^\s*\d+[.)]\s+(.+)$", cut)
            for i in bullets + numbered:
                i = i.strip()
                if i and not i.startswith("```"):
                    items.append(i)
            # セクション内のJSON
            jm = re.search(r"```json\s*(\{.*?\})\s*```", cut, re.DOTALL)
            if jm:
                try:
                    jd = json.loads(jm.group(1))
                    for k in [
                        "NEXT_ACTIONS",
                        "next_actions",
                        "action",
                        "actions",
                        "todo",
                        "todos",
                        "task",
                        "tasks",
                    ]:
                        v = jd.get(k)
                        if isinstance(v, str) and v.strip():
                            items.append(v.strip())
                        elif isinstance(v, list):
                            items.extend([str(x).strip() for x in v if str(x).strip()])
                except Exception:
                    pass
    except Exception:
        pass

    # 2) 全文フォールバック（まだ無ければ）
    if not items:
        bullets = re.findall(r"(?m)^\s*(?:[-・*]\s+)(.+)$", text)
        numbered = re.findall(r"(?m)^\s*\d+[.)]\s+(.+)$", text)
        for i in bullets + numbered:
            i = i.strip()
            if i and not i.startswith("```"):
                items.append(i)

    # 正規化 & 去重 & 上限
    seen = set()
    out: list[str] = []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
        if len(out) >= 10:
            break
    return out


def _load_agent_config() -> dict:
    import os

    from src.core.prompt_loader import load_governance

    try:
        gov = load_governance()
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


def _agent_memory_append(path: str, record: dict) -> None:
    import datetime as dt
    import json
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    rec = dict(record)
    rec["ts"] = dt.datetime.now().isoformat()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _agent_postprocess(output: dict, cfg: dict) -> None:
    agent = (cfg or {}).get("agent", {}) or {}
    mem = agent.get("memory") or {}
    if not agent.get("enabled"):
        return
    if mem.get("enabled") and output:
        path = mem.get("path") or "data/agent_memory.jsonl"
        _agent_memory_append(path, {"decision": output})


# --- agent decide wrapper (auto-appended) ---
try:
    _ORIG_DECIDE = KingNoctria.decide

    def _DECIDE_WRAPPED(self, *args, **kwargs):
        d = _ORIG_DECIDE(self, *args, **kwargs)
        try:
            _agent_postprocess(d, getattr(self, "_agent_cfg", {}))
        except Exception:
            pass
        return d

    KingNoctria.decide = _DECIDE_WRAPPED
except Exception:
    pass
