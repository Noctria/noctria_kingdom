# [NOCTRIA_CORE_REQUIRED]
# src/core/prompt_loader.py
from __future__ import annotations

import glob
import io
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# プロジェクトルート -> docs/governance を指す（このファイルは src/core/ 配下）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOV_DIR = PROJECT_ROOT / "docs" / "governance"


# ------------------------------------------------------------
# 小物: ディープマージ / 配列化 / YAMLローダ
# ------------------------------------------------------------
def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """dict を深くマージ（b が a を上書き）。"""
    for k, v in (b or {}).items():
        if k in a and isinstance(a[k], dict) and isinstance(v, dict):
            a[k] = _deep_merge(a[k], v)
        else:
            a[k] = v
    return a


def _as_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return [str(i) for i in x]
    return [str(x)]


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        loader = yaml.SafeLoader(f)
        loader.name = str(path)  # !include の相対解決に使う
        data = loader.get_single_data() or {}
    return data


# ------------------------------------------------------------
# !include タグ & パターン解決
# ------------------------------------------------------------
def _merge_from_patterns(pattern: str, base_file: Path) -> Dict[str, Any]:
    """パターン（相対/絶対・glob可）から候補を探し、読み込んでディープマージして返す。"""
    if not Path(pattern).is_absolute():
        # 1) include元ファイルの親 2) governance 直下
        candidates = glob.glob(str((base_file.parent / pattern).resolve()))
        candidates += glob.glob(str((GOV_DIR / pattern).resolve()))
        # 3) 見つからない場合は governance 配下を再帰探索（例: "doc_ops.yaml" 単体名）
        if not candidates and "/" not in pattern and "\\" not in pattern:
            candidates = [str(p) for p in GOV_DIR.rglob(pattern)]
    else:
        candidates = glob.glob(pattern)

    merged: Dict[str, Any] = {}
    seen: set[str] = set()
    for c in candidates:
        p = Path(c)
        if not p.exists():
            continue
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        d = _load_with_includes(p)  # 再帰読み込み（!include / includes 両対応）
        merged = _deep_merge(merged, d)
    return merged


def _include_constructor(loader: yaml.SafeLoader, node: yaml.Node):
    value = loader.construct_scalar(node)
    base_file = Path(getattr(loader, "name", GOV_DIR))
    return _merge_from_patterns(value, base_file)


# YAML ローダへ !include を登録
yaml.SafeLoader.add_constructor("!include", _include_constructor)


# ------------------------------------------------------------
# includes/include キー対応（配列・文字列・glob 可）
# ------------------------------------------------------------
def _resolve_key_includes(data: Dict[str, Any], base_file: Path) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return data

    inc_list: List[str] = []
    for k in ("includes", "include"):
        v = data.get(k)
        if v is not None:
            inc_list.extend(_as_list(v))

    # キー自体はマージ前に取り除く（最終出力に残さない）
    data = dict(data)
    data.pop("includes", None)
    data.pop("include", None)

    merged = dict(data)
    for pat in inc_list:
        inc_dict = _merge_from_patterns(pat, base_file)
        merged = _deep_merge(merged, inc_dict)
    return merged


# ------------------------------------------------------------
# 中核: ファイル読み込み（フォールバックで裸の !include 群も解釈）
# ------------------------------------------------------------
def _load_with_includes(path: Path) -> Dict[str, Any]:
    """
    1) 通常: YAML としてロード（!include タグ/ includes キーを解決）
    2) 失敗時: 裸の `!include foo.yaml` を行ごとにパースして順次マージ
    """
    text = path.read_text(encoding="utf-8")

    # まず通常の YAML として解釈
    try:
        with path.open("r", encoding="utf-8") as f:
            loader = yaml.SafeLoader(f)
            loader.name = str(path)
            data = loader.get_single_data() or {}
        # さらに includes/include キーを解決（再帰）
        return _resolve_key_includes(data, path)
    except yaml.YAMLError:
        pass  # フォールバックへ

    # フォールバック: 行単位で `!include` を拾ってマージ
    merged: Dict[str, Any] = {}
    base_file = path
    for line in text.splitlines():
        m = re.match(r"^\s*!include\s+(.+?)\s*$", line)
        if not m:
            continue
        pattern = m.group(1).strip()
        inc = _merge_from_patterns(pattern, base_file)
        merged = _deep_merge(merged, inc)

    return merged


# ------------------------------------------------------------
# 公開 API
# ------------------------------------------------------------
def load_governance(root_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    docs/governance/king_ops_prompt.yaml を起点に、!include / includes を
    再帰解決して統合辞書を返す。
    """
    if root_file is None:
        root_file = GOV_DIR / "king_ops_prompt.yaml"
    return _load_with_includes(root_file)


def render_system_prompt(gov: Dict[str, Any]) -> str:
    """
    統合済みガバナンス辞書から、王の System Prompt を合成する。
    - Charter / Principles は先頭に
    - Policies / Resource Policy / Operating / Guardrails があれば続ける
    - 最後に出力フォーマット規定
    """
    buf = io.StringIO()

    charter = gov.get("charter", {}) or {}
    name = charter.get("name", "Noctria 王")
    role = charter.get("role", "")
    mission = charter.get("mission", "")

    principles = gov.get("principles", []) or charter.get("principles", [])
    policies = gov.get("policies", {}) or gov.get("policy", {})
    resource_policy = gov.get("resource_policy", {})
    operating = gov.get("operating", {})
    guardrails = gov.get("guardrails", {})

    buf.write(f"You are {name}.\n")
    if role:
        buf.write(f"ROLE: {role}\n")
    if mission:
        buf.write(f"MISSION: {mission}\n")

    if principles:
        buf.write("PRINCIPLES:\n")
        for p in principles:
            buf.write(f"- {p}\n")

    if policies:
        buf.write("POLICIES:\n")
        for k, v in policies.items():
            buf.write(f"- {k}: {v}\n")

    if resource_policy:
        buf.write("RESOURCE_POLICY:\n")
        for k, v in resource_policy.items():
            buf.write(f"- {k}: {v}\n")

    if operating:
        buf.write("OPERATING_PROCEDURES:\n")
        for k, v in operating.items():
            buf.write(f"- {k}: {v}\n")

    if guardrails:
        buf.write("GUARDRAILS:\n")
        for k, v in guardrails.items():
            buf.write(f"- {k}: {v}\n")

    # 出力フォーマット規定（王の応答の一貫性確保）
    buf.write(
        "\nOUTPUT_FORMAT:\n"
        "- Always respond in Japanese.\n"
        "- Return a concise PLAN with numbered steps, plus RISKS and NEXT_ACTIONS.\n"
        "- When proposing code changes, output minimal, testable diffs or shell commands.\n"
        "- Prefer terse, actionable items over long prose.\n"
    )

    return buf.getvalue()
