# src/strategies/hermes_cognitor.py
# -*- coding: utf-8 -*-
"""
🦉 Hermes Cognitor (feature_order準拠)
- Plan層の標準dict/feature_order/labelsを自然言語説明
- decision_id / caller / trace_id を返却
- 共通System Prompt(v1.5) を前置し、LLM（OpenAI）呼び出しに対応
- LLM不可時は安全なダミー要約へフォールバック
- 生成物は agent_logs（SQLite: src/codex_reports/pdca_log.db）へ任意保存
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

# 共通SPローダ
try:
    from codex.prompts.loader import load_noctria_system_prompt  # v1.5 を想定
except Exception:  # ローダ未配置でも動作させる

    def load_noctria_system_prompt(_v: str) -> str:
        return "You are Noctria Kingdom common system prompt (fallback)."


# -----------------------------------------------------------------------------
# ログ設定
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
LOG = logging.getLogger("HermesCognitor")


# -----------------------------------------------------------------------------
# OpenAI クライアント選択（新API優先→旧APIフォールバック）
# -----------------------------------------------------------------------------
def _choose_openai_client():
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_NOCTRIA")
    if not api_key:
        return None, None
    try:
        from openai import OpenAI  # type: ignore

        return "new", OpenAI(api_key=api_key)
    except Exception:
        try:
            import openai  # type: ignore

            openai.api_key = api_key
            return "old", openai
        except Exception:
            return None, None


# -----------------------------------------------------------------------------
# DB（agent_logs）  ※run_pdca_agents.py と同テーブル互換
# -----------------------------------------------------------------------------
def _db_path() -> Path:
    root = Path(__file__).resolve().parents[2]  # project root
    return Path(os.getenv("NOCTRIA_PDCA_DB", str(root / "src" / "codex_reports" / "pdca_log.db")))


def _db_connect() -> Optional[sqlite3.Connection]:
    try:
        dbp = _db_path()
        dbp.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(dbp)
        # 最低限のスキーマ（存在しない場合のみ軽く作成）
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT,
                role TEXT,
                title TEXT,
                content TEXT,
                created_at TEXT
            );
            """
        )
        return conn
    except Exception as e:
        LOG.warning("agent_logs DB接続に失敗: %s", e)
        return None


def _db_log_agent(role: str, title: str, content: str, trace_id: Optional[str]) -> None:
    conn = _db_connect()
    if not conn:
        return
    try:
        jst = dt.timezone(dt.timedelta(hours=9))
        ts = dt.datetime.now(tz=jst).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO agent_logs (trace_id, role, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (trace_id or "", role, title, content, ts),
        )
        conn.commit()
    except Exception as e:
        LOG.warning("agent_logs への書き込みに失敗: %s", e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# -----------------------------------------------------------------------------
# プロンプト
# -----------------------------------------------------------------------------
COMMON_SP = load_noctria_system_prompt("v1.5")

HERMES_SYSTEM_PROMPT = (
    COMMON_SP
    + """

あなたは Noctria 王国の説明AI『Hermes Cognitor』です。
役割:
- Plan層から渡される特徴量(dict)と feature_order、要因ラベル(labels)をもとに、
  戦略意図・根拠・前提・リスク・想定シナリオ・撤退条件を、簡潔かつ具体的に日本語で説明します。
- ファンダメンタルズ分析とテクニカル分析の両面を接続し、相互の整合を言語化します。
- Fintokeiポリシー（ギャンブル的行為の禁止、1アイデアでの過剰リスク>3%の禁止、再現性重視）に反しない助言に限定します。

出力方針:
- 箇条書き中心（見出し＋短文）。断定より確率/条件言及を好む。
- 「なぜその指標が有効か」「逆シナリオは何か」「何で撤退するか」を必ず含める。
- 余計な美辞麗句は不要。トレード実務で使うためのメモに徹する。

出力JSONスキーマ:
{
  "summary": "1〜2文の要約",
  "rationale": ["根拠1", "根拠2", "..."],        // TA/FAの両軸を混ぜてOK
  "risk_notes": ["主要リスク/代替シナリオ", "..."],
  "exit_rules": ["撤退条件(例: SL/時間/ニュース)", "..."],
  "assumptions": ["前提・必要条件", "..."],
  "notes": ["補足(データ品質/相関/イベント注意)", "..."]
}
"""
)

DEFAULT_MODEL = os.getenv("NOCTRIA_GPT_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"


# -----------------------------------------------------------------------------
# 本体
# -----------------------------------------------------------------------------
class HermesCognitorStrategy:
    def __init__(self, model: str = DEFAULT_MODEL, feature_order: Optional[List[str]] = None):
        self.model = model
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER

    # ---- プロンプト構築（ユーザーメッセージ） ----
    def _build_user_prompt(
        self,
        features: Dict[str, Any],
        labels: List[str],
        feature_order: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> str:
        fo = feature_order or self.feature_order
        payload = {
            "feature_order": fo,
            "features": features,
            "labels": labels,
            "hint_reason": reason or "",
        }
        return (
            "次の入力を読み、上記の JSON スキーマで返答してください（日本語・JSONのみ）。\n"
            + json.dumps(payload, ensure_ascii=False)
        )

    # ---- LLM呼び出し ----
    def _call_llm(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        mode, client = _choose_openai_client()
        if not client:
            return None
        try:
            if mode == "new":
                resp = client.chat.completions.create(  # type: ignore
                    model=self.model,
                    messages=[
                        {"role": "system", "content": HERMES_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                txt = (resp.choices[0].message.content or "{}").strip()
            else:
                # 旧API
                resp = client.ChatCompletion.create(  # type: ignore
                    model=self.model,
                    messages=[
                        {"role": "system", "content": HERMES_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                )
                txt = (resp["choices"][0]["message"]["content"] or "{}").strip()

            data = json.loads(txt)
            if not isinstance(data, dict):
                return None
            # 最低限のキー補完
            data.setdefault("summary", "")
            data.setdefault("rationale", [])
            data.setdefault("risk_notes", [])
            data.setdefault("exit_rules", [])
            data.setdefault("assumptions", [])
            data.setdefault("notes", [])
            return data
        except Exception as e:
            LOG.warning("Hermes LLM 呼び出しに失敗: %s", e)
            return None

    # ---- ダミー（フォールバック） ----
    @staticmethod
    def _fallback_summary(labels: List[str]) -> Dict[str, Any]:
        head = labels[0] if labels else "特徴量・要因からの戦略説明"
        return {
            "summary": f"[ダミー要約] {head}",
            "rationale": ["データ指示に基づく短期モメンタム/平均回帰の可能性を評価"],
            "risk_notes": ["イベント急変・高ボラ銘柄のスリッページ", "想定と逆方向の持続トレンド"],
            "exit_rules": ["事前SL到達", "想定ニュース否定", "時間的撤退（当日クローズ）"],
            "assumptions": ["データの欠損・遅延が閾値内", "相関・重複シグナルが許容内"],
            "notes": ["実運用は Noctus Gate のロット・リスク制約に従う"],
        }

    # ---- 外部API（Plan層） ----
    def summarize_strategy(
        self,
        features: Dict[str, Any],
        labels: List[str],
        feature_order: Optional[List[str]] = None,
        reason: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_prompt = self._build_user_prompt(features, labels, feature_order, reason)
        LOG.info("HermesCognitor: プロンプト構築完了 / model=%s", self.model)

        out = self._call_llm(user_prompt) or self._fallback_summary(labels)
        # agent_logs へ保存（任意）
        try:
            _db_log_agent(
                role="hermes",
                title="Hermes Explanation",
                content=json.dumps(out, ensure_ascii=False),
                trace_id=trace_id,
            )
        except Exception:
            pass
        return out

    # ---- Strategyインターフェース ----
    def propose(
        self,
        input_data: Dict[str, Any],
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
    ) -> Dict[str, Any]:
        features = input_data.get("features", {}) or {}
        labels = input_data.get("labels", []) or []
        feature_order = input_data.get("feature_order", self.feature_order)
        reason = input_data.get("reason", "")
        trace_id = input_data.get("trace_id")

        explanation_obj = self.summarize_strategy(
            features=features,
            labels=labels,
            feature_order=feature_order,
            reason=reason,
            trace_id=trace_id,
        )

        return {
            "name": "HermesCognitor",
            "type": "llm_explanation_report",
            "explanation": explanation_obj,  # ← JSON構造で返す
            "feature_order": feature_order,
            "source_features": features,
            "labels": labels,
            "reason": reason,
            "llm_model": self.model,
            "decision_id": decision_id,
            "caller": caller,
            "trace_id": trace_id,
        }
