from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any

INVENTOR_SYSTEM_PROMPT = """\
あなたは Noctria 王国の開発者AI『Inventor Scriptus』です。
役割: 失敗したテストに対し、原因仮説→修正方針→具体的な変更点を提案します。
制約:
- いきなり大改修せず、最小差分でテストを通す方針を優先
- 王国のコーディング規約（contractsの後方互換、observability統一）を尊重
- 変更は「パッチ候補（擬似diff）」「対象ファイル」「対象関数」を明記して提示
出力形式:
- "summary": 要約
- "root_causes": 箇条書き
- "patch_suggestions": [{file, function, pseudo_diff, rationale}]
- "followup_tests": 追試案
"""

@dataclass
class PatchSuggestion:
    file: str
    function: str
    pseudo_diff: str
    rationale: str

@dataclass
class InventorOutput:
    summary: str
    root_causes: List[str]
    patch_suggestions: List[PatchSuggestion]
    followup_tests: List[str]

def propose_fixes(pytest_result: Dict[str, Any]) -> InventorOutput:
    """超シンプルなヒューリスティック: 失敗名とトレースを見て最小修正案を返す"""
    failures = pytest_result.get("failures", [])
    suggestions: List[PatchSuggestion] = []

    for f in failures[:3]:
        name = f.get("nodeid", "")
        tb = f.get("traceback", "")
        # 例: quality/noctus系の典型エラーに対するテンプレ
        if "test_noctus_gate_block" in name and "AttributeError" in tb and "context.get" in tb:
            suggestions.append(PatchSuggestion(
                file="src/plan_data/strategy_adapter.py",
                function="_bundle_to_dict_and_order",
                pseudo_diff="""\
--- a/src/plan_data/strategy_adapter.py
+++ b/src/plan_data/strategy_adapter.py
@@
-    ctx = features.context or {}
-    for k, v in ctx.items():
+    ctx = getattr(features, "context", None)
+    if ctx:
+        ctx_dict = ctx.dict() if hasattr(ctx, "dict") else dict(ctx)
+        for k, v in ctx_dict.items():
             key = f"ctx_{k}" if k not in base else k
             if key not in base:
                 base[key] = v
""",
                rationale="FeatureContext が pydantic モデルでも動くよう .dict() に対応"
            ))
        elif "QUALITY" in tb and "emit_alert" in tb:
            suggestions.append(PatchSuggestion(
                file="src/plan_data/quality_gate.py",
                function="emit_quality_alert",
                pseudo_diff="(必要に応じて kind='QUALITY.*' 形式へ正規化)",
                rationale="テスト期待の 'QUALITY' ベースに合わせる/既に通っていれば不要"
            ))
        else:
            suggestions.append(PatchSuggestion(
                file="(検出できず) 要ログ確認",
                function="(N/A)",
                pseudo_diff="(N/A)",
                rationale=f"失敗 {name} をログで詳細確認し、最小差分修正を作成"
            ))

    return InventorOutput(
        summary="失敗テストに対する最小修正案の下書き",
        root_causes=[f.get("message", "不明") for f in failures],
        patch_suggestions=suggestions,
        followup_tests=["pytest -q tests/test_quality_gate_alerts.py tests/test_noctus_gate_block.py"]
    )
