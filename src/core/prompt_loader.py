# src/core/prompt_loader.py
from __future__ import annotations

"""
Prompt loader/builder for Noctria.

- SSOT: docs/governance/king_ops_prompt.yaml
- Optional: Merge additional fragments under docs/governance/king_ops_sections/*.yaml
- Output: Markdown-like, model-friendly system prompt text usable by both Ollama and GPT API.
"""

import json
from pathlib import Path
from typing import Any, Mapping, Iterable, Optional, Dict, List

import yaml

# ====== Defaults ======
DEFAULT_SSOT = "docs/governance/king_ops_prompt.yaml"
DEFAULT_SECTIONS_DIR = "docs/governance/king_ops_sections"

# セクションの推奨順
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


# ====== Core API (legacy) ======
def load_governance(path: str | Path = DEFAULT_SSOT) -> Dict[str, Any]:
    """
    Legacy: Load ONLY the SSOT YAML file and return as dict (no sections merge).
    新コードでは load_governance_dict() の使用を推奨。
    """
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data or {}


def render_system_prompt(governance: Dict[str, Any]) -> str:
    """
    Render governance dict into Markdown-like system prompt text.
    """
    parts: List[str] = []
    ordered_keys = _order_keys(governance.keys(), RECOMMENDED_SECTION_ORDER)
    for k in ordered_keys:
        parts.append(_flatten_section(k, governance[k]))
    return "\n".join(parts).strip() + "\n"


def load_prompt_text(
    ssot_path: str = DEFAULT_SSOT,
    sections_dir: Optional[str] = DEFAULT_SECTIONS_DIR,
    strict: bool = False,
    prefer_sections: bool = True,
    order: Optional[Iterable[str]] = None,
    json_contract: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Convenience wrapper: YAML -> dict -> Markdown text
    - SSOT と sections をマージしてから Markdown 風テキストを組み立てる
    """
    base_map = _read_yaml_map(ssot_path, strict=strict)

    merged = dict(base_map)
    if sections_dir:
        frags = _read_sections_dir(sections_dir, strict=strict)
        merged = _merge_maps(base_map, frags, prefer_sections=prefer_sections)

    ordered_keys = _order_keys(merged.keys(), order or RECOMMENDED_SECTION_ORDER)
    parts = []
    for k in ordered_keys:
        parts.append(_flatten_section(k, merged[k]))

    if json_contract:
        parts.append("## Output Format (HARD REQUIREMENT)")
        parts.append(
            "- Return ONLY a single JSON object matching the schema below. "
            "No explanations or prose outside JSON."
        )
        schema_str = json.dumps(json_contract, ensure_ascii=False, indent=2)
        parts.append("```json\n" + schema_str + "\n```")
        parts.append("")

    return "\n".join(parts).strip() + "\n"


# === New: dictを返す高機能ローダ（sections込み） ===
def load_governance_dict(
    ssot_path: str = DEFAULT_SSOT,
    sections_dir: Optional[str] = DEFAULT_SECTIONS_DIR,
    *,
    strict: bool = False,
    prefer_sections: bool = True,
) -> Dict[str, Any]:
    """
    SSOT + sections/*.yaml をマージした dict を返す。
    - text が欲しい場合は load_prompt_text()
    - dict が欲しい場合は本関数を使う（king_noctria/agent_runner 等）
    """
    base_map = _read_yaml_map(ssot_path, strict=strict)
    if sections_dir:
        frags = _read_sections_dir(sections_dir, strict=strict)
        return _merge_maps(base_map, frags, prefer_sections=prefer_sections)
    return base_map


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
        for k, v in data.items():
            agg[k] = v
    return agg


def _merge_maps(
    base: Dict[str, Any],
    overlay: Dict[str, Any],
    prefer_sections: bool = True,
) -> Dict[str, Any]:
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
    bullet = "-"
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
