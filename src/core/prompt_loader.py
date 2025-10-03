# src/core/prompt_loader.py
from __future__ import annotations

"""
Prompt loader/builder for Noctria.

- SSOT: docs/governance/king_ops_prompt.yaml
- Optional: Merge additional fragments under docs/governance/king_ops_sections/*.yaml
- Output: Markdown-like, model-friendly system prompt text usable by both Ollama and GPT API.

Usage:
    from src.core.prompt_loader import load_prompt_text
    system_prompt = load_prompt_text()  # default SSOT
"""

import json
from pathlib import Path
from typing import Any, Mapping, Sequence, Iterable, Optional, Dict, List

import yaml

# ====== Defaults ======
DEFAULT_SSOT = "docs/governance/king_ops_prompt.yaml"
DEFAULT_SECTIONS_DIR = "docs/governance/king_ops_sections"

# セクションの推奨順（存在しないキーは無視、余ったキーは末尾に自然順で付与）
RECOMMENDED_SECTION_ORDER: List[str] = [
    "charter",
    "roles_raci",
    "agent",
    "ai_guidelines",
    "governance_reviews",
    "contracts",
    "rules",
    "routing",
    "automation_gates",
    "tools",
    "testing",
    "observability",
    "security",
    "slo",
    "cadence",
    "runbooks",
    "handover",
    "decision_rules",
    "decision_registry",
    "kpi_definitions",
    "kpi_alerts",
]


# ====== Public API ======
def load_prompt_text(
    ssot_path: str = DEFAULT_SSOT,
    sections_dir: Optional[str] = DEFAULT_SECTIONS_DIR,
    strict: bool = False,
    prefer_sections: bool = True,
    order: Optional[Iterable[str]] = None,
    json_contract: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build a model-ready system prompt string.

    Args:
        ssot_path: Path to the main YAML (SSOT).
        sections_dir: If provided, merge *.yaml in this directory (top-level dicts only).
        strict: If True, raise on missing files/invalid YAML. If False, continue best-effort.
        prefer_sections: When True and a key exists in both SSOT and section files, sections override.
        order: Custom section order (list of keys). Non-listed keys are appended in natural order.
        json_contract: Optional JSON schema-ish dict to append as “Output format” hard rule.

    Returns:
        Markdown-like text suitable for system prompt.
    """
    base_map = _read_yaml_map(ssot_path, strict=strict)

    merged = dict(base_map)
    if sections_dir:
        frags = _read_sections_dir(sections_dir, strict=strict)
        merged = _merge_maps(base_map, frags, prefer_sections=prefer_sections)

    # シリアライズ（YAML→Markdown風整形）
    ordered_keys = _order_keys(merged.keys(), order or RECOMMENDED_SECTION_ORDER)
    parts = []
    for k in ordered_keys:
        parts.append(_flatten_section(k, merged[k]))

    # 追加で JSON 出力契約を付けたい場合
    if json_contract:
        parts.append("## Output Format (HARD REQUIREMENT)")
        parts.append(
            "- Return ONLY a single JSON object matching the schema below. "
            "No explanations or prose outside JSON."
        )
        # スキーマは可読性のため整形して提示（モデルはテキストとして読む）
        schema_str = json.dumps(json_contract, ensure_ascii=False, indent=2)
        parts.append("```json\n" + schema_str + "\n```")
        parts.append("")

    return "\n".join(parts).strip() + "\n"


# ====== Helpers ======
def _read_yaml_map(path: str | Path, strict: bool = False) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        if strict:
            raise FileNotFoundError(f"SSOT not found: {p}")
        return {}
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as e:
        if strict:
            raise ValueError(f"Invalid YAML at {p}: {e}") from e
        return {}
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        if strict:
            raise ValueError(f"Top-level must be a mapping in {p}")
        return {}
    return dict(data)


def _read_sections_dir(dir_path: str | Path, strict: bool = False) -> Dict[str, Any]:
    d = Path(dir_path)
    if not d.exists():
        if strict:
            raise FileNotFoundError(f"Sections dir not found: {d}")
        return {}

    agg: Dict[str, Any] = {}
    for fp in sorted(d.glob("*.yaml")):
        try:
            data = yaml.safe_load(fp.read_text(encoding="utf-8"))
        except Exception as e:
            if strict:
                raise ValueError(f"Invalid YAML at {fp}: {e}") from e
            else:
                continue
        if data is None:
            continue
        if not isinstance(data, Mapping):
            if strict:
                raise ValueError(f"Top-level must be a mapping in {fp}")
            else:
                continue
        # ファイル名（拡張子なし）をキーの候補として使う or 中身のキーをマージ
        # ここでは「中身の top-level キー」をすべてマージ（同名キーがあれば後勝ち）
        for k, v in data.items():
            agg[k] = v
    return agg


def _merge_maps(
    base: Dict[str, Any],
    overlay: Dict[str, Any],
    prefer_sections: bool = True,
) -> Dict[str, Any]:
    """
    Shallow merge. When keys collide:
        - prefer_sections=True  -> overlay wins
        - prefer_sections=False -> base wins
    """
    if prefer_sections:
        merged = dict(base)
        merged.update(overlay)
        return merged
    else:
        merged = dict(overlay)
        merged.update(base)
        return merged


def _order_keys(keys: Iterable[str], preferred: Iterable[str]) -> List[str]:
    ks = list(keys)
    preferred = [k for k in preferred if k in ks]
    rest = sorted([k for k in ks if k not in preferred])
    return preferred + rest


def _flatten_section(title: str, content: Any) -> str:
    lines = [f"## {title}"]
    _append_lines(lines, content, level=0)
    lines.append("")
    return "\n".join(lines)


def _append_lines(lines: List[str], content: Any, level: int) -> None:
    bullet = "-"  # 単純な箇条書き
    indent = "  " * level

    if isinstance(content, Mapping):
        for k, v in content.items():
            if isinstance(v, (Mapping, list, tuple)):
                lines.append(f"{indent}{bullet} **{k}**:")
                _append_lines(lines, v, level + 1)
            else:
                lines.append(f"{indent}{bullet} **{k}**: {v}")
    elif isinstance(content, (list, tuple)):
        for it in content:
            if isinstance(it, (Mapping, list, tuple)):
                lines.append(f"{indent}{bullet}")
                _append_lines(lines, it, level + 1)
            else:
                lines.append(f"{indent}{bullet} {it}")
    else:
        lines.append(f"{indent}{bullet} {content}")


# ====== Optional: quick CLI for debugging ======
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build system prompt from YAML.")
    parser.add_argument("--ssot", default=DEFAULT_SSOT, help="Path to SSOT YAML")
    parser.add_argument(
        "--sections",
        default=DEFAULT_SECTIONS_DIR,
        help="Dir with additional *.yaml fragments (set '' to disable)",
    )
    parser.add_argument("--strict", action="store_true", help="Strict mode")
    parser.add_argument(
        "--no-prefer-sections",
        action="store_true",
        help="Base SSOT should override sections on conflict",
    )
    parser.add_argument(
        "--with-json-contract",
        default="",
        help="Path to a JSON file with output schema to append (optional)",
    )
    args = parser.parse_args()

    contract = None
    if args.with_json_contract:
        p = Path(args.with_json_contract)
        if p.exists():
            contract = json.loads(p.read_text(encoding="utf-8"))

    text = load_prompt_text(
        ssot_path=args.ssot,
        sections_dir=(args.sections or None),
        strict=args.strict,
        prefer_sections=not args.no_prefer_sections,
        json_contract=contract,
    )
    print(text)