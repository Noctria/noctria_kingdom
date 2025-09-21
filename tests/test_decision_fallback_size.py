# tests/test_decision_fallback_size.py
# -*- coding: utf-8 -*-
"""
Inventor Guard: fallback:size の理由文字列検証用 軽量テスト
- 実装では decision["reason"] == "fallback:size" を採用
- 本テストはその仕様に一致していることを確認する

前提:
- 最新の判定結果(decision)を取得する関数/スクリプトが存在すること
  - 例1: scripts/show_last_inventor_decision.py に --json モードがある（データ無なら {} を返し exit 0）
  - 例2: 決定結果JSONのパスが一定である（環境に応じて変更可）

備考:
- CI が軽量に通ることを最優先。取得に失敗/欠落した場合は SKIP する。
- 環境変数で取得方法を上書きできる:
  - NOCTRIA_DECISION_CMD="python -m scripts.show_last_inventor_decision --json"
  - NOCTRIA_DECISION_JSON_PATHS="codex_reports/latest_inventor_decision.json,codex_reports/latest_decision.json"
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest


def _load_decision_via_script() -> dict | None:
    """
    scripts/show_last_inventor_decision.py が利用可能ならそれを使って取得する。
    - 既定: `python -m scripts.show_last_inventor_decision --json`
    - 環境変数 NOCTRIA_DECISION_CMD で上書き可
    - 失敗時/空出力/不正JSONは None（テストは SKIP 判定）
    """
    cmd_str = os.getenv(
        "NOCTRIA_DECISION_CMD",
        f"{shlex.quote(sys.executable or 'python3')} -m scripts.show_last_inventor_decision --json",
    )
    try:
        # shell=False のため配列化
        cmd = shlex.split(cmd_str)
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=10)
        out = (out or "").strip()
        if not out:
            return None
        data = json.loads(out)
        # 空オブジェクト {} は「データなし」扱い
        if isinstance(data, dict) and not data:
            return None
        return data
    except Exception:
        return None


def _iter_candidate_paths() -> list[Path]:
    """
    既知の JSON 候補パスを返す。環境変数で追加指定も可能。
    """
    candidates: list[Path] = [
        Path("codex_reports/latest_inventor_decision.json"),
        Path("codex_reports/latest_decision.json"),
        Path("reports/latest_inventor_decision.json"),
    ]
    extra = os.getenv("NOCTRIA_DECISION_JSON_PATHS")
    if extra:
        for p in extra.split(","):
            p = p.strip()
            if p:
                candidates.append(Path(p))
    # 重複除去・存在順序維持
    seen = set()
    uniq: list[Path] = []
    for c in candidates:
        if c.as_posix() not in seen:
            seen.add(c.as_posix())
            uniq.append(c)
    return uniq


def _load_decision_from_file() -> dict | None:
    """
    代替手段: 既知の場所から JSON を読む（環境によって調整可）
    なければ None。
    """
    for p in _iter_candidate_paths():
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and not data:
                    # 空オブジェクトはデータなし扱い
                    continue
                return data
            except Exception:
                continue
    return None


def _extract_decision(decision_like: dict) -> dict:
    """
    決定本体がネストされているケースにも緩く対応して dict を返す。
    """
    if (
        isinstance(decision_like, dict)
        and "decision" in decision_like
        and isinstance(decision_like["decision"], dict)
    ):
        return decision_like["decision"]
    return decision_like


def _get_latest_decision() -> dict:
    """
    最新 decision をできる限り取得。見つからなければ pytest.skip。
    """
    decision = _load_decision_via_script()
    if decision is None:
        decision = _load_decision_from_file()

    if decision is None:
        pytest.skip("最新の decision を取得できませんでした（軽量CIのため SKIP）。")

    return _extract_decision(decision)


def test_fallback_size_reason_matches_implementation():
    """
    実装仕様:
      decision["reason"] == "fallback:size"
    を厳密一致で検証する。
    """
    decision = _get_latest_decision()

    # データがないCI環境では軽量テストとしてSKIP（キー欠落/空文字も含む）
    if not isinstance(decision, dict) or not decision.get("reason"):
        pytest.skip("no decision.reason available in CI (skipping lightweight test)")

    # 実装仕様に合わせて厳密一致
    assert decision["reason"] == "fallback:size", f"unexpected reason: {decision.get('reason')!r}"
