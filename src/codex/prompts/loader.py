# src/codex/prompts/loader.py
from __future__ import annotations

"""
Noctria 共通 System Prompt ローダー

- 既定の正本: docs/prompts/noctria_agent_guidelines_v{version}.md
- 既定バージョン: v1.5
- 環境変数での上書き:
    - NOCTRIA_SYSTEM_PROMPT_PATH   … 明示パスを直接指定（最優先）
    - NOCTRIA_SYSTEM_PROMPT_VERSION… バージョンを指定（例: v1.5）
- 使い方:
    from codex.prompts.loader import load_noctria_system_prompt
    system_prompt = load_noctria_system_prompt()  # v1.5 を読み込み
"""

import os
from pathlib import Path
from typing import Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# パス解決
# ──────────────────────────────────────────────────────────────────────────────


def _project_root() -> Path:
    """
    本ファイル: <ROOT>/src/codex/prompts/loader.py
    -> ROOT は loader.py の 3 つ上の親ディレクトリ
    """
    return Path(__file__).resolve().parents[3]


def _default_version() -> str:
    return os.getenv("NOCTRIA_SYSTEM_PROMPT_VERSION", "v1.5").strip() or "v1.5"


def _default_prompt_path(version: str) -> Path:
    # 正本は docs/prompts/noctria_agent_guidelines_vX.Y.md
    root = _project_root()
    return root / "docs" / "prompts" / f"noctria_agent_guidelines_{version}.md"


def _resolve_prompt_path(version: Optional[str] = None) -> Tuple[Path, str]:
    """
    実際に読み込む markdown の Path と、採用されたバージョン文字列を返す。
    優先順位:
      1) NOCTRIA_SYSTEM_PROMPT_PATH（明示パス）
      2) docs/prompts/noctria_agent_guidelines_{version}.md
    """
    env_path = os.getenv("NOCTRIA_SYSTEM_PROMPT_PATH", "").strip()
    if env_path:
        p = Path(env_path).expanduser().resolve()
        return p, f"(env:{p.name})"

    ver = (version or _default_version()).strip()
    return _default_prompt_path(ver), ver


# ──────────────────────────────────────────────────────────────────────────────
# 読み込み・整形
# ──────────────────────────────────────────────────────────────────────────────


def _read_text_utf8(path: Path) -> str:
    # UTF-8/BOM 等を考慮して読み出す
    text = path.read_text(encoding="utf-8", errors="strict")
    # 改行を LF に正規化
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 末尾に必ず 1 改行（API で誤連結されにくくする）
    if not text.endswith("\n"):
        text += "\n"
    return text


# シンプルなメモリキャッシュ（プロセス内）
_CACHE: dict[str, str] = {}


def load_noctria_system_prompt(version: Optional[str] = None, strict: bool = True) -> str:
    """
    Noctria 共通 System Prompt を読み込んで返す。

    :param version: "v1.5" のようなバージョン指定。None の場合は環境変数または既定値。
    :param strict:  True のとき、ファイルが無ければ例外を投げる。
                    False のとき、簡易フォールバック文面を返す。
    :return: system prompt (Markdown 全文)
    """
    path, resolved_ver = _resolve_prompt_path(version)

    cache_key = f"{resolved_ver}::{path}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    if not path.exists():
        if strict:
            raise FileNotFoundError(
                f"[NoctriaPrompt] Prompt file not found: {path} "
                f"(version={resolved_ver}). "
                f"Set NOCTRIA_SYSTEM_PROMPT_PATH or place the file under docs/prompts/."
            )
        # フォールバック（最小限のガード付き）
        fallback = f"""# Noctria System Prompt (FALLBACK)
This is a minimal fallback system prompt because the configured file was not found.
- version: {resolved_ver}
- expected path: {path}

You are a cautious engineering assistant. If you are asked to modify code,
prefer minimal, reversible changes and preserve test compatibility.
If information is missing, ask concise clarifying questions first.
"""
        _CACHE[cache_key] = fallback
        return fallback

    text = _read_text_utf8(path)
    _CACHE[cache_key] = text
    return text


# ──────────────────────────────────────────────────────────────────────────────
# CLI / デバッグ用
# ──────────────────────────────────────────────────────────────────────────────


def _main(argv: Optional[list[str]] = None) -> int:
    """
    手元確認用:
      $ python -m codex.prompts.loader
      or
      $ python src/codex/prompts/loader.py v1.5
    """
    import sys

    args = list(argv or sys.argv[1:])
    ver = args[0] if args else None
    try:
        prompt = load_noctria_system_prompt(version=ver, strict=True)
        print(prompt)
        return 0
    except Exception as e:
        print(f"[NoctriaPrompt] ERROR: {e}", file=sys.stderr)
        # strict フォールバックに切り替えた上で出力
        prompt = load_noctria_system_prompt(version=ver, strict=False)
        print(prompt)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
