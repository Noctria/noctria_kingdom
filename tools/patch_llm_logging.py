#!/usr/bin/env python3
"""
Patch LLM logging:

- Targets (already load .env):
    - noctria_gui/main.py
    - llm_server/main.py
    - scripts/run_pdca_agents.py
    - src/codex/run_codex_cycle.py

- Adds once per file:
    1) safe imports: `import os`, `import logging`
    2) a one-shot env flags line:
       logging.info(
         "LLM flags: enabled=%s mode=%s base=%s model=%s", ...)
    3) a helper `_log_llm_usage(resp)` if not present
    4) after lines like:
         resp = client.chat.completions.create(...)
       append:
         _log_llm_usage(resp)

Notes:
- Only appends usage logging when the call result is assigned
  to a simple name on its own statement (safe).
- Idempotent: running multiple times won't duplicate inserts.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import List

ROOT = Path(".")
TARGETS = [
    ROOT / "noctria_gui" / "main.py",
    ROOT / "llm_server" / "main.py",
    ROOT / "scripts" / "run_pdca_agents.py",
    ROOT / "src" / "codex" / "run_codex_cycle.py",
]

USAGE_HELPER = r'''
def _log_llm_usage(resp):
    """Best-effort logging of OpenAI-like usage fields."""
    try:
        import logging  # local import safe
        u = getattr(resp, "usage", None)
        if u is not None:
            pt = getattr(u, "prompt_tokens", None)
            ct = getattr(u, "completion_tokens", None)
            tt = getattr(u, "total_tokens", None)
            logging.info("LLM usage prompt=%s completion=%s total=%s", pt, ct, tt)
        else:
            logging.info("LLM usage unavailable (provider?)")
    except Exception as _e:
        logging.exception("LLM usage logging failed: %s", _e)
'''.lstrip("\n")

FLAGS_LOG_LINE = (
    "logging.info("
    '"LLM flags: enabled=%s mode=%s base=%s model=%s", '
    'os.getenv("NOCTRIA_LLM_ENABLED"), '
    'os.getenv("NOCTRIA_HARMONIA_MODE"), '
    'os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL"), '
    'os.getenv("NOCTRIA_GPT_MODEL") or os.getenv("OPENAI_MODEL"))'
)


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8").replace("\r\n", "\n")
    except FileNotFoundError:
        return ""


def write(p: Path, s: str) -> None:
    if not s.endswith("\n"):
        s += "\n"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def ensure_import(src: str, name: str) -> str:
    if re.search(rf"(?m)^\s*import\s+{re.escape(name)}\s*$", src):
        return src
    # Insert after __future__ and module docstring if any, else very top.
    lines = src.splitlines()
    i = 0
    # shebang/coding line(s)
    while i < len(lines) and (lines[i].startswith("#!") or "coding" in lines[i]):
        i += 1
    # module docstring
    if i < len(lines) and re.match(r'^\s*(?:[ruRU]{0,2}["\']{3})', lines[i]):
        # skip docstring block
        quote = lines[i].lstrip()[0:3] if lines[i].lstrip().startswith(("'''", '"""')) else None
        i += 1
        if quote:
            while i < len(lines):
                if quote in lines[i]:
                    i += 1
                    break
                i += 1
    # from __future__ imports
    while i < len(lines) and lines[i].startswith("from __future__ import"):
        i += 1
    lines.insert(i, f"import {name}")
    return "\n".join(lines)


def ensure_flags_log(src: str) -> str:
    if "LLM flags:" in src:
        return src
    # place right after first load_dotenv(...) if present, else after imports
    m = re.search(r"(?m)^\s*load_dotenv\([^)]*\)\s*$", src)
    if m:
        insert_at = m.end()
        return src[:insert_at] + "\n" + FLAGS_LOG_LINE + "\n" + src[insert_at:]
    # fallback: after first block of imports
    m = re.search(r"(?m)^(?:from\s+\S+\s+import\s+.*|import\s+\S+)\s*$", src)
    if not m:
        return FLAGS_LOG_LINE + "\n" + src
    # find end of contiguous import block
    lines = src.splitlines()
    start = m.start()
    # compute end line index of contiguous imports from the first match
    first_line = src[: m.start()].count("\n")
    idx = first_line
    while idx < len(lines) and re.match(
        r"^\s*(?:from\s+\S+\s+import\s+.*|import\s+\S+)\s*$", lines[idx]
    ):
        idx += 1
    # insert after idx-1
    pos = len("\n".join(lines[:idx]))
    return src[:pos] + "\n" + FLAGS_LOG_LINE + "\n" + src[pos:]


def ensure_usage_helper(src: str) -> str:
    if re.search(r"(?m)^def\s+_log_llm_usage\s*\(", src):
        return src
    # put helper near the bottom after imports (or right after flags log if present)
    # simplest: append at the end with a separating newline
    if not src.endswith("\n"):
        src += "\n"
    return src + "\n" + USAGE_HELPER


def add_usage_after_assignment_calls(src: str) -> str:
    """
    Look for simple forms like:
        resp = client.chat.completions.create(...)

    After the closing paren of that call (same logical statement),
    insert:
        _log_llm_usage(resp)

    Handles multi-line parentheses. Only operates when the LHS is a
    simple name and the call is a standalone statement.
    """
    text = src
    pattern = re.compile(
        r"""(?m)^(?P<ind>\s*)(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*
             (?P<call>[^#\n]*?client\s*\.\s*chat\s*\.\s*completions\s*\.\s*create\s*\()
        """,
        re.X,
    )

    def find_call_end(s: str, start_idx: int) -> int | None:
        # find matching ')' from start_idx (which is after the '(')
        depth = 1
        i = start_idx
        in_str = None
        escape = False
        while i < len(s):
            ch = s[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == in_str:
                    in_str = None
            else:
                if ch in ("'", '"'):
                    in_str = ch
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        # consume optional trailing spaces
                        j = i + 1
                        while j < len(s) and s[j] in " \t":
                            j += 1
                        # statement should end at newline or comment
                        # allow a trailing comment; we will insert before it
                        return j
            i += 1
        return None

    offset = 0
    out_parts: List[str] = []
    last_idx = 0
    for m in pattern.finditer(text):
        ind = m.group("ind")
        var = m.group("var")
        call_open_idx = m.end("call")  # position just after '('
        call_end = find_call_end(text, call_open_idx)
        if call_end is None:
            continue  # give up if we can't find the end safely

        # ensure this matched region is a standalone statement line(s)
        # i.e., next non-space char after call_end until newline is either '#' or '\n'
        nl = text.find("\n", call_end)
        if nl == -1:
            nl = len(text)
        tail = text[call_end:nl]
        if tail.strip() not in ("",) and not tail.lstrip().startswith("#"):
            continue  # not a clean statement

        # append previous untouched chunk
        out_parts.append(text[last_idx:nl])
        # insert usage line just before newline
        insert = f"\n{ind}_log_llm_usage({var})"
        out_parts.append(insert)
        last_idx = nl  # continue from newline

    out_parts.append(text[last_idx:])
    return "".join(out_parts)


def patch_one(p: Path) -> bool:
    src = read(p)
    if not src:
        return False
    before = src

    # 1) imports
    src = ensure_import(src, "os")
    src = ensure_import(src, "logging")

    # 2) flags line
    src = ensure_flags_log(src)

    # 3) helper
    src = ensure_usage_helper(src)

    # 4) usage after assignment calls
    src = add_usage_after_assignment_calls(src)

    if src != before:
        write(p, src)
        print(f"[patched] {p.as_posix()}")
        return True
    else:
        print(f"[noop] {p.as_posix()}")
        return False


def main():
    any_change = False
    for t in TARGETS:
        any_change |= patch_one(t)
    if not any_change:
        print("No changes made (already patched).")


if __name__ == "__main__":
    main()
