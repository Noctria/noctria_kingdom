# =========================
# File: src/execution/risk_policy.py
# =========================
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
except Exception:  # PyYAML 未導入でも動くようフォールバック
    yaml = None


# ─────────────────────────────────────────────────────────────────────────────
# 既定ポリシー（risk_gate.apply_risk_policy が期待する dict 形）
#  - default: 全シンボル共通の上限や時間帯
#  - overrides: シンボル毎の上書き
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_POLICY: Dict[str, Any] = {
    "default": {
        "trading_hours_utc": ["00:00-23:59"],  # 例 "08:00-22:00"
        "max_consecutive_losses": 0,
        "shrink_after_losses_pct": 50,         # N連敗以上で qty を%縮小
        "max_order_qty": 5_000.0,              # 単発注文の上限
        "max_position_notional": 50_000.0,     # 総量上限（簡易）
        "forbidden_symbols": [],               # 完全禁止シンボル
    },
    "overrides": {
        # 例:
        # "USDJPY": {"max_order_qty": 10_000}
    },
}


def _coerce_policy_types(pol: Dict[str, Any]) -> Dict[str, Any]:
    """
    型をだいたい整える（数値/配列/文字列など）。不正値は寛容に既定へ寄せる。
    """
    out = {"default": dict(DEFAULT_POLICY["default"]), "overrides": {}}

    d = dict(out["default"])
    src_d = dict(pol.get("default") or {})
    # 数値系
    for k, cast in (
        ("max_order_qty", float),
        ("max_position_notional", float),
        ("shrink_after_losses_pct", float),
        ("max_consecutive_losses", int),
    ):
        if k in src_d:
            try:
                d[k] = cast(src_d[k])
            except Exception:
                pass

    # 配列/文字列系
    th = src_d.get("trading_hours_utc", d["trading_hours_utc"])
    if isinstance(th, str):
        th = [th]
    if not (isinstance(th, list) and all(isinstance(x, str) for x in th)):
        th = d["trading_hours_utc"]
    d["trading_hours_utc"] = th

    forb = src_d.get("forbidden_symbols", d["forbidden_symbols"])
    if isinstance(forb, str):
        forb = [forb]
    if not (isinstance(forb, list) and all(isinstance(x, str) for x in forb)):
        forb = d["forbidden_symbols"]
    d["forbidden_symbols"] = forb

    out["default"] = d

    # overrides
    ov = pol.get("overrides") or {}
    if isinstance(ov, dict):
        for sym, conf in ov.items():
            if not isinstance(sym, str) or not isinstance(conf, dict):
                continue
            out["overrides"][sym] = dict(conf)
    return out


def _normalize_loaded(data: Any) -> Dict[str, Any]:
    """
    読み込んだ YAML を正規化して dict 形に。
    - ルートに default/overrides があればそのまま採用
    - 無ければ「ルート直下のキー群」を default に入れる簡易形も許容
    """
    if not isinstance(data, dict):
        return dict(DEFAULT_POLICY)

    if "default" in data or "overrides" in data:
        # 既定と浅くマージ（欠損キーは埋める）
        merged = {
            "default": {**DEFAULT_POLICY["default"], **(data.get("default") or {})},
            "overrides": {**DEFAULT_POLICY.get("overrides", {}), **(data.get("overrides") or {})},
        }
        return _coerce_policy_types(merged)

    # 簡易形：root 直下のキーを default とみなす
    merged = {
        "default": {**DEFAULT_POLICY["default"], **data},
        "overrides": dict(DEFAULT_POLICY["overrides"]),
    }
    return _coerce_policy_types(merged)


def load_policy(path: Optional[str] = None) -> Dict[str, Any]:
    """
    リスクポリシーを読み込んで dict を返す（risk_gate がこの形を期待）。
    優先度:
      1) 引数 path
      2) 環境変数 NOCTRIA_RISK_POLICY
      3) 'configs/risk_policy.yml'
    読み込み失敗や PyYAML 不在時は DEFAULT_POLICY を返す。
    """
    candidate = Path(
        path
        or os.getenv("NOCTRIA_RISK_POLICY", "configs/risk_policy.yml")
    )

    if yaml is None or not candidate.exists():
        return dict(DEFAULT_POLICY)

    try:
        with candidate.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        return _normalize_loaded(loaded)
    except Exception:
        # 破損・フォーマット不正は黙って既定にフォールバック（運用でログ追加はお好みで）
        return dict(DEFAULT_POLICY)


__all__ = ["load_policy", "DEFAULT_POLICY"]
