#!/usr/bin/env python3
# coding: utf-8
from __future__ import annotations

"""
🦉 Hermes Cognitor (feature_order準拠, API/ローカル自動切替)
- Plan層の標準 dict / feature_order / labels を自然言語説明に変換
- decision_id / caller も返却
- 環境変数:
  - NOCTRIA_HERMES_MODE=api|offline|auto  (優先)
  - HERMES_USE_OPENAI=1                   (後方互換フラグ、あれば api 扱い)
  - OPENAI_API_KEY=...                    (API 利用時に必須)
  - NOCTRIA_OPENAI_MODEL / OPENAI_MODEL   (モデル指定、既定: gpt-4o-mini)
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List

from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

# -----------------------------------------------------------------------------
# Logger（Airflow タスクロガーに寄せつつ、ローカルでも動作）
# -----------------------------------------------------------------------------
LOGGER = logging.getLogger("airflow.task")
if not LOGGER.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# -----------------------------------------------------------------------------
# モード判定
# -----------------------------------------------------------------------------
def _env_mode() -> str:
    """
    Hermes の実行モードを決定する。
    - NOCTRIA_HERMES_MODE が優先（offline/api/auto）
    - 未設定なら HERMES_USE_OPENAI=1 を互換的に解釈して api
    - それ以外は offline
    """
    mode = (os.getenv("NOCTRIA_HERMES_MODE") or "").strip().lower()
    if mode in {"offline", "api", "auto"}:
        return mode
    if os.getenv("HERMES_USE_OPENAI", "0") == "1":
        return "api"
    return "offline"


# -----------------------------------------------------------------------------
# 本体
# -----------------------------------------------------------------------------
class HermesCognitorStrategy:
    def __init__(
        self,
        model: str = None,
        feature_order: Optional[List[str]] = None,
    ):
        self.model = model or os.getenv("NOCTRIA_OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER

    # --- Prompt ---------------------------------------------------------------
    def _build_prompt(
        self,
        features: Dict[str, Any],
        labels: List[str],
        feature_order: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        OpenAI v1 chat.completions 用の messages を返す
        """
        fo = feature_order or self.feature_order

        sys_msg = (
            "あなたは Noctria 王国の伝令AI『Hermes Cognitor』です。"
            "与えられた標準特徴量と要因ラベルから、投資戦略の意図を日本語で簡潔・具体に要約します。"
            "箇条書きで重要点を3〜6項目、最後に1行の結論を添えてください。"
        )
        usr_payload = {
            "feature_order": fo,
            "features": features,
            "labels": labels,
            "reason": reason or "",
        }
        user_msg = (
            "以下の入力を要約してください。"
            "出力は Markdown。見出し→箇条書き（3〜6項目）→最後に太字の最終判断。"
            f"\n\n入力(JSON):\n{json.dumps(usr_payload, ensure_ascii=False, indent=2)}"
        )
        return [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ]

    # --- API 経由 -------------------------------------------------------------
    def _summarize_via_api(
        self,
        features: Dict[str, Any],
        labels: List[str],
        feature_order: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> Optional[str]:
        try:
            from openai import OpenAI  # v1 client
        except Exception:
            LOGGER.warning("[Hermes] openai パッケージ未導入のため API を使用できません。")
            return None

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_NOCTRIA")
        if not api_key:
            LOGGER.warning("[Hermes] OPENAI_API_KEY 未設定のため API を使用できません。")
            return None

        client = OpenAI(api_key=api_key)
        model = self.model
        msgs = self._build_prompt(features, labels, feature_order, reason)

        try:
            LOGGER.info("[Hermes] プロンプト組み立て完了")
            resp = client.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=0.2,
                max_tokens=400,
            )
            text = (resp.choices[0].message.content or "").strip()
            # usage ログ（あれば）
            try:
                u = getattr(resp, "usage", None)
                if u:
                    LOGGER.info(
                        "[Hermes] API usage: prompt=%s completion=%s total=%s",
                        getattr(u, "prompt_tokens", None),
                        getattr(u, "completion_tokens", None),
                        getattr(u, "total_tokens", None),
                    )
            except Exception:
                pass
            return text or None
        except Exception as e:
            LOGGER.exception("[Hermes] API 呼び出しに失敗: %s", e)
            return None

    # --- ローカル要約（フォールバック） ---------------------------------------
    def _summarize_locally(
        self,
        features: Dict[str, Any],
        labels: List[str],
        feature_order: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> str:
        fo = feature_order or self.feature_order
        # シンプルなテンプレ要約（テストやオフライン時の代替）
        bullets: List[str] = []
        if reason:
            bullets.append(f"理由の要旨: {reason[:140]}{'…' if len(reason) > 140 else ''}")
        if labels:
            bullets.append(f"主因ラベル: {', '.join(labels[:5])}{' ほか' if len(labels) > 5 else ''}")
        if features:
            # 代表値を数個ピック
            keys = [k for k in fo if k in features] or list(features.keys())
            head = keys[:5]
            preview = ", ".join(f"{k}={features.get(k)!r}" for k in head)
            bullets.append(f"主要特徴量: {preview}{' ほか' if len(keys) > 5 else ''}")

        if not bullets:
            bullets = ["入力特徴量・ラベルから特筆事項は検出されませんでした。"]

        md = [
            "## 市場戦略の説明（ローカル生成）",
            "",
            *[f"- {b}" for b in bullets],
            "",
            "**結論:** 条件付きで様子見（詳細判断は追加データ次第）",
        ]
        return "\n".join(md)

    # --- 外部 API/ローカルを自動選択 ------------------------------------------
    def summarize_strategy(
        self,
        features: Dict[str, Any],
        labels: List[str],
        feature_order: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> str:
        mode = _env_mode()
        LOGGER.info("[Hermes] mode=%s", mode)
        if mode in {"api", "auto"}:
            out = self._summarize_via_api(features, labels, feature_order, reason)
            if out:
                return out
            LOGGER.info("[Hermes] API 失敗のためローカル要約にフォールバックします。")
        return self._summarize_locally(features, labels, feature_order, reason)

    # --- ラッパ（PDCA から使いやすい形で） -----------------------------------
    def propose(
        self,
        input_data: Dict[str, Any],
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
    ) -> Dict[str, Any]:
        features = input_data.get("features", {})
        labels = input_data.get("labels", [])
        feature_order = input_data.get("feature_order", self.feature_order)
        reason = input_data.get("reason", "")

        explanation = self.summarize_strategy(features, labels, feature_order, reason)
        return {
            "name": "HermesCognitor",
            "type": "llm_explanation_report",
            "explanation": explanation,
            "feature_order": feature_order,
            "source_features": features,
            "labels": labels,
            "reason": reason,
            "llm_model": self.model,
            "decision_id": decision_id,
            "caller": caller,
        }

    # --- Markdown 化（レポート保存で便利） ------------------------------------
    @staticmethod
    def to_markdown(explanation: str, meta: Optional[Dict[str, Any]] = None) -> str:
        lines = ["# 🦉 Hermes Cognitor — 説明レポート", ""]
        if meta:
            lines += [f"- model: `{meta.get('llm_model')}`",
                      f"- decision_id: `{meta.get('decision_id')}`" if meta.get("decision_id") else "",
                      f"- caller: `{meta.get('caller')}`" if meta.get("caller") else "",
                      ""]
        lines.append(explanation.strip())
        return "\n".join([l for l in lines if l is not None])
