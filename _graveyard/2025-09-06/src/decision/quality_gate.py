# src/decision/quality_gate.py
from __future__ import annotations

"""
Decision 層からの DataQualityGate 利用を、Plan 層実装へ一本化するシム（再エクスポート）。

- 依存の重複と実装乖離を防ぐため、Plan 層の定義をそのまま公開します。
- 既存コードの `from decision.quality_gate import DataQualityGate` などは
  変更なしで動作します（APIそのまま）。

将来的に Plan 側のモジュール名/構造を変更する場合は、ここだけ直せば Decision 層の互換は維持できます。
"""

try:
    # 公式実装（単一の正典）へ委譲
    from plan_data.quality_gate import DataQualityGate, QualityAssessment  # type: ignore
except Exception as e:  # pragma: no cover
    # もし import に失敗したら、そのまま例外を投げて気づけるようにする
    # （ここでサイレントフォールバックはしない）
    raise

__all__ = ["DataQualityGate", "QualityAssessment"]
