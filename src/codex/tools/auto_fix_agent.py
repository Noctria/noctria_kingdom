# src/codex/tools/auto_fix_agent.py
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

LOG = logging.getLogger("auto_fix_agent")
if not LOG.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

RUFF_JSON_DEFAULT = Path("src/codex_reports/ruff/last_run.json")  # ruff_runnerが吐くパス
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # …/noctria_kingdom

# ---------------------------
# ユーティリティ
# ---------------------------
def run(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    LOG.info("Running: %s", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    if p.stdout:
        LOG.debug("stdout:\n%s", p.stdout)
    if p.stderr:
        LOG.debug("stderr:\n%s", p.stderr)
    return p.returncode, p.stdout, p.stderr


def load_ruff_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Ruff JSON not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_file(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write_file(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


# ---------------------------
# ルール別の安全ミニ修正
# ---------------------------
def fix_f401_unused_import(code: str, message: str, line_no: int) -> str:
    """
    F401: 'X' imported but unused
    - 単一行importから未使用名を取り除く（残りゼロなら行ごと削除）
    - from ... import a, b の一部だけ未使用: その名前だけ削る
    """
    lines = code.splitlines()
    idx = line_no - 1
    if not (0 <= idx < len(lines)):
        return code

    target = lines[idx]
    # message例: "'pathlib.Path' imported but unused"
    m = re.search(r"'([^']+)' imported but unused", message)
    if not m:
        return code
    imported = m.group(1)  # 例: pathlib.Path or Path

    # from x import a, b, c
    if re.match(r"^\s*from\s+\S+\s+import\s+", target):
        # 名前部分を分解して imported の末尾名を削る
        # imported が "pathlib.Path" のような場合、末尾名だけ照合
        imported_name = imported.split(".")[-1]
        head, names = target.split("import", 1)
        parts = [p.strip() for p in names.split(",")]
        parts_new = [p for p in parts if p.split(" as ")[0].strip() != imported_name]
        if parts_new:
            lines[idx] = f"{head}import " + ", ".join(parts_new)
        else:
            # すべて無くなったら行ごと除去
            lines[idx] = ""
    # import x, y as z
    elif re.match(r"^\s*import\s+", target):
        tokens = target.replace("import", "", 1).strip()
        parts = [p.strip() for p in tokens.split(",")]
        # imported の最初のトークン（例: pathlib）
        imported_root = imported.split(".")[0]
        def root_of(part: str) -> str:
            # "pathlib as pb" -> pathlib
            return part.split(" as ")[0].strip().split(".")[0]
        parts_new = [p for p in parts if root_of(p) != imported_root]
        if parts_new:
            lines[idx] = "import " + ", ".join(parts_new)
        else:
            lines[idx] = ""
    else:
        # import行ではなかった（誤差防止）
        return code

    # 連続空行を1つに
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def fix_f841_unused_local(code: str, message: str, line_no: int) -> str:
    """
    F841: local variable 'X' is assigned to but never used
    - 代入行の左辺名を _ に置換（副作用保持）
    """
    lines = code.splitlines()
    idx = line_no - 1
    if not (0 <= idx < len(lines)):
        return code
    m = re.search(r"Local variable `?'?([^`']+)`?'? is assigned to but never used", message)
    var = m.group(1) if m else None
    if not var:
        return code

    # 代入の先頭変数だけ安全に _ へ（= より左側の単純ケース）
    pattern = re.compile(rf"^(\s*){re.escape(var)}(\s*=\s*)")
    lines[idx] = pattern.sub(r"\1_\2", lines[idx])
    return "\n".join(lines)


def fix_e402_import_position(code: str, message: str, line_no: int) -> str:
    """
    E402: module level import not at top of file
    - 対象行が import 行なら、ファイル先頭のimportブロックへ“移動”
    - 過剰移動を避けるため、単一行のみ（相対的に安全）
    """
    lines = code.splitlines()
    idx = line_no - 1
    if not (0 <= idx < len(lines)):
        return code
    line = lines[idx]
    if not re.match(r"^\s*(from\s+\S+\s+import\s+|import\s+)", line):
        return code

    # 行を抜いて、先頭のdocstring/コメント後の最初のimportブロックの直後に挿入
    moved = line
    lines[idx] = ""

    insert_at = 0
    # shebang / encoding / モジュールdocstring/冒頭コメントをスキップ
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if i == 0 and (s.startswith("#!") or "coding" in s):
            i += 1
            continue
        if s.startswith('"""') or s.startswith("'''"):
            # シンプル: 三連クォートをもう一度見つける
            q = s[:3]
            i += 1
            while i < len(lines) and q not in lines[i]:
                i += 1
            if i < len(lines):
                i += 1
            continue
        if s.startswith("#"):
            i += 1
            continue
        break
    insert_at = i

    # 既存importの直後をねらう（なければ insert_at の位置）
    j = insert_at
    while j < len(lines) and re.match(r"^\s*(from\s+\S+\s+import\s+|import\s+)", lines[j]):
        j += 1
    insert_pos = j

    # 挿入
    new_lines = lines[:insert_pos] + [moved] + lines[insert_pos:]
    # 余分な空行整理
    text = "\n".join(new_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# ---------------------------
# GPT/SoRoban エスカレーションの入口（任意）
# ---------------------------
def gpt_escalate(file_path: Path, code: str, diagnostics: List[Dict[str, Any]]) -> Optional[str]:
    """
    OPENAI_API_KEY 等があれば、未対応ルールをGPTに投げてパッチ案をもらう入口。
    ここでは雛形だけ（安全上、即時適用はせず将来拡張用）。
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_NOCTRIA")
    if not api_key:
        return None
    try:
        import openai  # type: ignore
    except Exception:
        return None

    prompt = {
        "file": str(file_path),
        "notes": "Return only the corrected file content. Keep changes minimal to satisfy Ruff.",
        "diagnostics": diagnostics[:25],
        "code_head": "\n".join(code.splitlines()[:2000]),  # 保険
    }
    try:
        resp = openai.chat.completions.create(  # type: ignore[attr-defined]
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You fix Python code to satisfy Ruff and keep minimal changes."},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=4000,
        )
        text = (resp.choices[0].message.content or "").strip()
        # 返却は「全体ファイルの新内容」を想定
        if len(text) > 0 and "\n" in text:
            return text
        return None
    except Exception as e:
        LOG.warning("GPT escalate failed: %s", e)
        return None


# ---------------------------
# メイン処理
# ---------------------------
RULE_FIXERS = {
    "F401": fix_f401_unused_import,
    "F841": fix_f841_unused_local,
    "E402": fix_e402_import_position,
}


def group_by_file(results: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """ruff JSONをファイル単位にまとめる"""
    files = {}
    for diag in results.get("results", []):
        path = diag.get("filename") or diag.get("file") or ""
        if not path:
            continue
        files.setdefault(path, []).append(diag)
    return files


def apply_fixes(path: Path, diags: List[Dict[str, Any]], use_gpt: bool) -> bool:
    code = read_file(path)
    original = code
    # ソート：行番号降順で安全に編集
    diags_sorted = sorted(
        diags,
        key=lambda d: (d.get("location", {}).get("row") or d.get("line") or 0),
        reverse=True,
    )
    unhandled: List[Dict[str, Any]] = []

    for d in diags_sorted:
        rule = d.get("code") or d.get("rule") or ""
        loc = d.get("location", {}) or {}
        row = loc.get("row") or d.get("line") or 0
        msg = d.get("message") or d.get("short_message") or ""

        fixer = RULE_FIXERS.get(rule)
        if fixer:
            try:
                code = fixer(code, msg, int(row))
            except Exception as e:
                LOG.warning("fixer %s failed on %s:%s: %s", rule, path, row, e)
                unhandled.append(d)
        else:
            unhandled.append(d)

    # GPTへの委譲（任意）
    if use_gpt and unhandled:
        patched = gpt_escalate(path, code, unhandled)
        if isinstance(patched, str) and len(patched) > 0:
            code = patched

    if code != original:
        write_file(path, code)
        LOG.info("Patched: %s", path)
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Auto-fix common Ruff errors and re-run ruff.")
    ap.add_argument("--ruff-json", default=str(RUFF_JSON_DEFAULT), help="Path to ruff JSON report")
    ap.add_argument("--use-gpt", action="store_true", help="Escalate unhandled rules to GPT if API key is set")
    ap.add_argument("--paths", nargs="*", default=[], help="Optional subset of files to consider")
    ap.add_argument("--fix-rounds", type=int, default=2, help="Repeat fix/ruff cycles (default: 2)")
    ap.add_argument("--ruff-extra", default="", help="Extra args to pass to `ruff check`")
    args = ap.parse_args()

    root = PROJECT_ROOT
    os.chdir(root)

    changed_any = False
    for round_i in range(args.fix_rounds):
        LOG.info("=== Round %d: run ruff ===", round_i + 1)
        # ruff_runnerがあればそれを使用、なければ直接ruff
        rargs = ["python", "-m", "src.codex.tools.ruff_runner"]
        if args.paths:
            rargs.extend(args.paths)
        ret, out, err = run(rargs + ([] if args.ruff_extra == "" else [args.ruff_extra]))
        # ruff_runnerは JSON を RUFF_JSON_DEFAULT に保存するため、それを読む
        json_path = Path(args.ruff_json)
        if not json_path.exists():
            # 直接ruffにフォールバック
            cmd = ["ruff", "check", "--output-format", "json"]
            if args.paths:
                cmd.extend(args.paths)
            else:
                cmd.append(".")
            if args.ruff_extra:
                cmd.extend(args.ruff_extra.split())
            ret, out, err = run(cmd)
            if ret not in (0, 1):  # 0: OK, 1: 有違反
                LOG.error("ruff failed: %s", err.strip())
                return ret
            results = json.loads(out or "{}")
        else:
            results = load_ruff_json(json_path)

        files = group_by_file(results)
        if args.paths:
            # サブセット指定があればフィルタ
            keep = set(args.paths)
            files = {p: di for p, di in files.items() if p in keep or str(Path(p)) in keep}

        round_changed = False
        for rel, ds in files.items():
            path = (root / rel).resolve()
            # 代表的なルールのみ先に拾う（他はGPTへ）
            ds_focus = [d for d in ds if (d.get("code") in RULE_FIXERS) or args.use_gpt]
            if not ds_focus:
                continue
            if not path.exists():
                continue
            if apply_fixes(path, ds_focus, use_gpt=args.use_gpt):
                round_changed = True
                changed_any = True

        if not round_changed:
            LOG.info("No more changes in round %d.", round_i + 1)
            break

    # 最終チェック（表示用）
    _, out, _ = run(["ruff", "check"] + (args.paths if args.paths else []))
    print("==== Final Ruff ====")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
