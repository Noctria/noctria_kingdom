# src/plan_data/quality_gate.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal
from .contracts import FeatureBundle

Action = Literal["OK", "FLAT", "SCALE"]  # OK=通常 / FLAT=出力や提案を平坦化（抑制）/ SCALE=数量縮小

@dataclass
class QualityResult:
    ok: bool
    action: Action                 # "OK" | "FLAT" | "SCALE"
    qty_scale: float = 1.0
    reasons: List[str] = field(default_factory=list)
    # 監査・可観測性で使うための参照値（しきい値と実測値）
    max_lag_min: int = 0
    max_missing: float = 0.0
    data_lag_min: int = 0
    missing_ratio: float = 0.0

# --- 初期値（提案⑤ 初期値を継承） ---
DEFAULT_MAX_DATA_LAG_MIN = 30      # 30分遅延を超えたら抑制
DEFAULT_MAX_MISSING_RATIO = 0.05   # 5%超の欠損で縮小開始

def _clamp(v: float, lo: float, hi: float) -> float:
    return hi if v > hi else lo if v < lo else v

def evaluate_quality(
    bundle: FeatureBundle,
    *,
    max_lag_min: int = DEFAULT_MAX_DATA_LAG_MIN,
    max_missing: float = DEFAULT_MAX_MISSING_RATIO
) -> QualityResult:
    """
    データ品質ゲート（Plan層）:
      - data_lag_min（分）: 最新データの遅延（大きいほど悪い）
      - missing_ratio（0.0〜1.0）: 特徴量DFの欠損率（大きいほど悪い）

    判定ルール（簡易）:
      - data_lag_min > max_lag_min → action = "FLAT"（提案抑制）
      - missing_ratio > max_missing → action = "SCALE"（数量縮小; すでに FLAT なら FLAT を優先）
        * 縮小率は超過分に応じて線形に下げ、最小 0.3 にクランプ

    戻り値には、根拠出力用に実測値と閾値も同梱する。
    """
    ctx = bundle.context

    # 入力の妥当性（安全側に寄せる）
    if max_lag_min < 0:
        max_lag_min = 0
    # missing_ratio の閾値は 0..1 に制限
    max_missing = _clamp(float(max_missing), 0.0, 1.0)

    # コンテキスト側の値も安全化（存在・範囲）
    data_lag_min = getattr(ctx, "data_lag_min", 0) or 0
    missing_ratio = getattr(ctx, "missing_ratio", 0.0) or 0.0
    missing_ratio = _clamp(float(missing_ratio), 0.0, 1.0)

    reasons: List[str] = []
    action: Action = "OK"
    scale = 1.0

    # 1) データ遅延チェック
    if data_lag_min > max_lag_min:
        reasons.append(f"data_lag_min={data_lag_min} > max_lag_min={max_lag_min}")
        action = "FLAT"  # 抑制（数量縮小より強い扱い）

    # 2) 欠損率チェック
    if missing_ratio > max_missing:
        reasons.append(f"missing_ratio={missing_ratio:.3f} > max_missing={max_missing:.3f}")
        # 既に FLAT でなければ SCALE
        if action == "OK":
            action = "SCALE"
            # 超過分に応じて線形縮小（最小0.3）
            over = missing_ratio - max_missing
            scale = _clamp(1.0 - over * 2.0, 0.3, 1.0)
        else:
            # FLATが優先（抑制の方が強い）
            pass

    ok = (action == "OK")
    return QualityResult(
        ok=ok,
        action=action,
        qty_scale=scale,
        reasons=reasons,
        max_lag_min=max_lag_min,
        max_missing=max_missing,
        data_lag_min=int(data_lag_min),
        missing_ratio=float(missing_ratio),
    )
