#!/usr/bin/env python3
"""
Auto-fix loop (PDCA強化版)
- 失敗指紋(YAML)→修正ガイド注入
- 必須トークン検査(ファイル別)
- Few-shot 例の自動注入
- 段階テスト(軽→重) + 差分テスト
- 成果メトリクス(JSONL)記録
- 追加: 温度0.0 / トレースAllowlist / 回帰ゲート(失敗時ロールバック, 成功時のみcommit)

Usage:
  OPENAI_API_KEY=sk-... python scripts/auto_fix_loop.py --max-iters 5

環境変数:
  NOCTRIA_AUTOFIX_MODEL  : モデル名 (default: gpt-4o-mini)
  NOCTRIA_AUTOFIX_LIGHT  : "1" なら軽テスト優先 (default: 1)
  NOCTRIA_AUTOFIX_RUFF   : "1" なら ruff --fix 実行 (default: 1)
  NOCTRIA_AUTOFIX_BLACK  : "1" なら black 実行 (default: 1)
  NOCTRIA_AUTOFIX_COMMIT : "1" なら git commit (default: 1; ※成功時のみ実施)
"""

from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

# ===================== 設定 =====================

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DIRS = ("src/", "tests/")
MODEL = os.getenv("NOCTRIA_AUTOFIX_MODEL", "gpt-4o-mini")
MAX_ITERS = 5

# プロンプト・出力サイズガード
CTX_MAX_BYTES = 160_000
MAX_PATCH_BYTES = 300_000
MAX_TOTAL_PATCH_BYTES = 600_000

# 実行フラグ
RUN_RUFF = os.getenv("NOCTRIA_AUTOFIX_RUFF", "1") == "1"
RUN_BLACK = os.getenv("NOCTRIA_AUTOFIX_BLACK", "1") == "1"
GIT_COMMIT = os.getenv("NOCTRIA_AUTOFIX_COMMIT", "1") == "1"
LIGHT_FIRST = os.getenv("NOCTRIA_AUTOFIX_LIGHT", "1") == "1"

# ブランチ
BRANCH_PREFIX = "autofix"

# 追加ファイル（常に文脈に含める）
EXTRA_CONTEXT_FILES = [
    "pytest.ini",
    "pyproject.toml",
    "tests/conftest.py",
    "src/core/path_config.py",
]

# 失敗指紋・必須トークン・Few-shot 設定ファイル/ディレクトリ
FINGERPRINTS_YAML = ROOT / "scripts" / "autofix_fingerprints.yaml"
REQUIRED_TOKENS_JSON = ROOT / "scripts" / "autofix_required_tokens.json"
FEWSHOT_DIR = ROOT / "scripts" / "autofix_fewshots"

# メトリクス保存先
METRICS_JSONL = ROOT / "src" / "codex_reports" / "autofix_metrics.jsonl"

# ===================== ヘルパ =====================


@dataclass
class PytestResult:
    ok: bool
    code: int
    stdout: str
    stderr: str


def run(cmd: List[str], check=False, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, check=check, **kw)


def run_pytest(light: bool, target_tests: Optional[List[str]] = None) -> PytestResult:
    """
    light=True: 既定設定(heavy/gpu/external を skip する pytest.ini 前提) + 差分テスト優先
    light=False: 可能なら重め全体実行
    """
    base = ["pytest", "-q", "--maxfail=1", "--disable-warnings", "-rA"]
    args = base[:]
    if target_tests:
        args += target_tests
    proc = run(args, check=False)
    return PytestResult(
        ok=(proc.returncode == 0), code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr
    )


TB_FILE_RE = re.compile(r'File "([^"]+)", line (\d+), in ([^\n]+)')


def extract_trace_files(stdout: str, stderr: str, limit: int = 12) -> List[Tuple[Path, int, str]]:
    text = "\n".join([stdout[-30000:], stderr[-30000:]])
    hits = TB_FILE_RE.findall(text)
    out: List[Tuple[Path, int, str]] = []
    for fp, line, fn in hits[:limit]:
        p = Path(fp)
        try:
            ln = int(line)
        except Exception:
            ln = 1
        out.append((p, ln, fn))
    return out


def read_snippet(p: Path, around_line: int, radius: int = 36) -> Optional[str]:
    if not p.exists() or not p.is_file():
        return None
    try:
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return None
    i0 = max(0, around_line - radius - 1)
    i1 = min(len(lines), around_line + radius)
    snippet = []
    for idx in range(i0, i1):
        prefix = ">>" if (idx + 1) == around_line else "  "
        snippet.append(f"{prefix}{idx+1:5d}: {lines[idx]}")
    return "\n".join(snippet)


def collect_repo_context(
    trace_files: List[Tuple[Path, int, str]], extra_files: List[str] | None = None
) -> Dict:
    ctx_items = []
    added: set[str] = set()
    for p, ln, fn in trace_files:
        if not p.exists() or p.suffix not in (".py", ".toml", ".ini", ".cfg", ".yaml", ".yml"):
            continue
        key = str(p)
        if key in added:
            continue
        snippet = read_snippet(p, ln) or ""
        added.add(key)
        ctx_items.append({"path": key, "around_line": ln, "function": fn, "snippet": snippet})
    for extra in extra_files or []:
        pe = Path(extra)
        if pe.exists() and pe.is_file() and str(pe) not in added:
            try:
                txt = pe.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                txt = ""
            ctx_items.append(
                {"path": str(pe), "around_line": 1, "function": "", "snippet": txt[:10000]}
            )
            added.add(str(pe))
    payload = json.dumps(ctx_items, ensure_ascii=False)
    if len(payload.encode("utf-8")) > CTX_MAX_BYTES:
        ctx_items = ctx_items[: max(1, len(ctx_items) // 2)]
    return {"files": ctx_items}


def detect_changed_tests_from_patches(patches: List[Dict]) -> List[str]:
    """
    パッチに対応するテストを簡易に推定。
    - tests/ 下の直接パッチはそのまま対象
    - src/xxx.py に対しては tests/xxx*_test.py, tests/test_*xxx*.py を候補に
    """
    candidates: set[str] = set()
    for p in patches:
        path = p.get("path", "")
        if not path:
            continue
        if path.startswith("tests/") and path.endswith(".py"):
            candidates.add(path)
        elif path.startswith("src/") and path.endswith(".py"):
            stem = Path(path).stem
            for pat in [f"tests/{stem}*_test.py", f"tests/test_*{stem}*.py"]:
                for m in ROOT.glob(pat):
                    candidates.add(str(m.relative_to(ROOT)))
    return sorted(candidates)


# ===== Allowlist: トレースに出たパスのみ許可（src/, tests/ 配下に限る） =====


def build_trace_allowlist(trace_files: List[Tuple[Path, int, str]]) -> Set[str]:
    allow: Set[str] = set()
    for p, _, _ in trace_files:
        try:
            rel = str(p.relative_to(ROOT))
        except Exception:
            rel = str(p)
        if any(rel.startswith(d) for d in ALLOWED_DIRS):
            allow.add(rel)
    return allow


# ===================== 失敗指紋 / 必須トークン / Few-shot =====================


def load_fingerprints() -> List[Dict]:
    try:
        import yaml  # type: ignore
    except Exception:
        return []
    if not FINGERPRINTS_YAML.exists():
        return []
    try:
        data = yaml.safe_load(FINGERPRINTS_YAML.read_text(encoding="utf-8"))
        return data or []
    except Exception:
        return []


def match_fingerprints(stdout: str, stderr: str) -> List[Dict]:
    fps = load_fingerprints()
    text = "\n".join([stdout[-40000:], stderr[-40000:]])
    out: List[Dict] = []
    for f in fps:
        pat = f.get("when_stdout_regex") or f.get("when_stderr_regex")
        if not pat:
            continue
        try:
            if re.search(pat, text, re.S | re.M):
                out.append(f)
        except re.error:
            pass
    return out


def load_required_tokens() -> Dict[str, List[str]]:
    if not REQUIRED_TOKENS_JSON.exists():
        return {}
    try:
        return json.loads(REQUIRED_TOKENS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_fewshots() -> List[Dict]:
    fewshots: List[Dict] = []
    if not FEWSHOT_DIR.exists():
        return fewshots
    for f in FEWSHOT_DIR.glob("*.jsonl"):
        try:
            for ln in f.read_text(encoding="utf-8").splitlines():
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    obj = json.loads(ln)
                    if isinstance(obj, dict) and "patch" in obj:
                        fewshots.append(obj)
                except Exception:
                    continue
        except Exception:
            continue
    return fewshots[:6]


# ===================== プロンプト =====================

PROMPT_SYSTEM = """You are a senior Python engineer running an automated test-fixing loop.
You must ONLY return JSON that conforms to the requested schema. Do not include markdown fences or prose.
Constraints:
- Change ONLY files under these directories: {allowed_dirs}.
- Prefer minimal, surgical fixes.
- Output entire-file replacements (new content) instead of partial diffs.
- Keep code safe for offline CI (no network calls unless guarded/stubbed).
- Be careful with indentation, encoding, and imports placement.
- If the root cause is in tests vs src, fix whichever is clearly wrong; otherwise prefer src.
"""

PROMPT_USER_FMT = """Repository failing test summary:
Exit code: {code}

=== Pytest stdout (tail) ===
{stdout_tail}

=== Pytest stderr (tail) ===
{stderr_tail}

Files mentioned in tracebacks (with snippets):
{ctx_json}

Known failure fingerprints and guides (matched):
{fingerprints_json}

Few-shot examples (trimmed):
{fewshots_json}

Task:
- Propose one or more patches to make the failing test(s) pass.
- Return pure JSON with this schema:

{
  "reason": "short explanation",
  "patches": [
    {
      "path": "relative/path/under/src_or_tests.py",
      "new_content": "FULL new file content (UTF-8)",
      "why": "what changed"
    }
  ]
}

Rules:
- Only include files under {allowed_dirs}.
- Each "new_content" must be the complete new content for that file.
- No placeholders. No backticks.
- If you are not confident, return "patches": [] with a helpful "reason".
"""

# ===================== モデル呼び出し（堅牢化 + 温度0.0） =====================


def call_model(user_prompt: str) -> Dict:
    """
    OpenAI SDK の差異に耐える実装:
    1) responses.parse (新) があれば使う
    2) chat.completions with response_format={"type":"json_object"}
    3) responses.create + 手パース
    すべて temperature=0.0（決定性重視）
    """
    try:
        from openai import OpenAI
    except Exception:
        print("ERROR: openai package not installed. `pip install openai`", file=sys.stderr)
        raise

    client = OpenAI()
    system_msg = PROMPT_SYSTEM.format(allowed_dirs=list(ALLOWED_DIRS))

    # Path A: responses.parse
    try:
        resp = client.responses.parse(
            model=MODEL,
            input=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt},
            ],
            **{"response_format": {"type": "json_object"}},
            temperature=0.0,
        )
        txt = resp.output_text
        return json.loads(txt)
    except Exception:
        pass

    # Path B: chat.completions
    try:
        cc = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        txt = cc.choices[0].message.content
        return json.loads(txt)
    except Exception:
        pass

    # Path C: responses.create（手パース）
    try:
        resp = client.responses.create(
            model=MODEL,
            temperature=0.0,
            input=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt},
            ],
        )
        txt = getattr(resp, "output_text", None)
        if not txt:
            parts = []
            for item in getattr(resp, "output", []) or []:
                if hasattr(item, "content"):
                    parts.extend(
                        [c.text for c in item.content if getattr(c, "type", "") == "output_text"]
                    )
            txt = "\n".join(parts) if parts else ""
        return json.loads(txt)
    except Exception as e:
        return {"reason": f"model call failed: {e!r}", "patches": []}


# ===================== 検証・適用・ロールバック・メトリクス =====================


def validate_patches(
    patches: List[Dict],
    required_tokens: Dict[str, List[str]],
    allowed_paths: Optional[Set[str]] = None,
) -> Tuple[List[Dict], List[str]]:
    """
    - ディレクトリAllowlist（src/tests）
    - トレースAllowlist（allowed_paths が与えられたら、その中だけ許可）
    - 必須トークン検査
    - サイズガード
    """
    errors: List[str] = []
    total_bytes = 0
    valid: List[Dict] = []

    for i, p in enumerate(patches):
        path = p.get("path", "")
        new_content = p.get("new_content", "")
        if not path or not isinstance(path, str):
            errors.append(f"[{i}] missing/invalid path")
            continue
        if not any(path.startswith(d) for d in ALLOWED_DIRS):
            errors.append(f"[{i}] path not allowed: {path}")
            continue
        if allowed_paths is not None and path not in allowed_paths:
            errors.append(f"[{i}] path not in traceback allowlist: {path}")
            continue

        b = len(new_content.encode("utf-8", errors="ignore"))
        if b == 0:
            errors.append(f"[{i}] empty content for {path}")
            continue
        if b > MAX_PATCH_BYTES:
            errors.append(f"[{i}] single patch too large ({b} bytes)")
            continue

        # 必須トークン検査
        req = required_tokens.get(path) or required_tokens.get(str(Path(path)))
        if not req:
            from fnmatch import fnmatch

            for key, toks in required_tokens.items():
                if "*" in key or "?" in key:
                    if fnmatch(path, key):
                        req = toks
                        break
        if req:
            missing = [tok for tok in req if tok not in new_content]
            if missing:
                errors.append(f"[{i}] required tokens missing in {path}: {missing}")
                continue

        total_bytes += b
        valid.append({"path": path, "new_content": new_content, "why": p.get("why", "")})

    if total_bytes > MAX_TOTAL_PATCH_BYTES:
        errors.append(f"total patches too large ({total_bytes} bytes)")
        valid = []
    return valid, errors


def apply_patches_with_backups(patches: List[Dict]) -> List[Tuple[Path, Optional[Path]]]:
    """
    ファイルごとに .autofix.bak を作ってから上書き。
    返り値: [(path, backup_path_or_None), ...]
    """
    applied: List[Tuple[Path, Optional[Path]]] = []
    for p in patches:
        path = Path(p["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        backup: Optional[Path] = None
        if path.exists():
            backup = path.with_suffix(path.suffix + ".autofix.bak")
            try:
                shutil.copy2(path, backup)
            except Exception:
                backup = None
        path.write_text(p["new_content"], encoding="utf-8")
        applied.append((path, backup))
    return applied


def format_code() -> None:
    if RUN_RUFF:
        run(["ruff", "check", "--fix", "src", "tests"], check=False)
    if RUN_BLACK:
        run(["black", "src", "tests"], check=False)


def rollback_files(applied: List[Tuple[Path, Optional[Path]]]) -> None:
    """
    バックアップがあれば復元。なければ削除（新規作成されたファイルの取り消し）。
    """
    for path, backup in applied:
        try:
            if backup and backup.exists():
                shutil.copy2(backup, path)
                backup.unlink(missing_ok=True)
            else:
                # 新規作成なら削除
                if path.exists():
                    path.unlink()
        except Exception:
            pass


def finalize_backups(applied: List[Tuple[Path, Optional[Path]]]) -> None:
    """成功確定後に .autofix.bak を掃除。"""
    for _, backup in applied:
        if backup and backup.exists():
            try:
                backup.unlink()
            except Exception:
                pass


def git_commit(message: str) -> None:
    run(["git", "add", "-A"], check=False)
    run(["git", "commit", "-m", message], check=False)


def log_metrics(payload: Dict) -> None:
    try:
        METRICS_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with METRICS_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ===================== メイン =====================


def ensure_branch():
    if not GIT_COMMIT:
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    name = f"{BRANCH_PREFIX}/{ts}"
    base = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    res = run(["git", "checkout", "-b", name])
    if res.returncode != 0:
        print(f"[warn] could not create branch {name}, staying on {base}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-iters", type=int, default=MAX_ITERS)
    args = ap.parse_args()

    ensure_branch()
    required_tokens = load_required_tokens()
    fewshots = load_fewshots()

    for it in range(1, args.max_iters + 1):
        print(f"\n=== Iteration {it} ===")

        # まず軽テスト
        start_ts = time.time()
        res_light = run_pytest(light=True)
        light_elapsed = time.time() - start_ts

        if res_light.ok:
            # 軽テストGREENなら重テスト（必要なら）
            if LIGHT_FIRST:
                start_ts2 = time.time()
                res_heavy = run_pytest(light=False)
                heavy_elapsed = time.time() - start_ts2
                if res_heavy.ok:
                    print("✅ GREEN — all tests passed.")
                    log_metrics(
                        {
                            "ts": int(time.time()),
                            "iter": it,
                            "result": "GREEN",
                            "model": MODEL,
                            "light_elapsed_sec": round(light_elapsed, 3),
                            "heavy_elapsed_sec": round(heavy_elapsed, 3),
                            "patches": 0,
                        }
                    )
                    return
                stdout_tail = res_heavy.stdout[-20000:]
                stderr_tail = res_heavy.stderr[-20000:]
                trace_files = extract_trace_files(res_heavy.stdout, res_heavy.stderr)
            else:
                print("✅ GREEN — (light tests).")
                log_metrics(
                    {
                        "ts": int(time.time()),
                        "iter": it,
                        "result": "GREEN_LIGHT_ONLY",
                        "model": MODEL,
                        "light_elapsed_sec": round(light_elapsed, 3),
                        "patches": 0,
                    }
                )
                return
        else:
            stdout_tail = res_light.stdout[-20000:]
            stderr_tail = res_light.stderr[-20000:]
            trace_files = extract_trace_files(res_light.stdout, res_light.stderr)

        # 文脈収集 & Allowlist
        fps = match_fingerprints(stdout_tail, stderr_tail)
        ctx = collect_repo_context(trace_files, EXTRA_CONTEXT_FILES)
        trace_allowlist = build_trace_allowlist(trace_files)

        # Few-shotを短文化
        compact_fs = []
        for ex in fewshots:
            compact_fs.append(
                {
                    "failure": str(ex.get("failure", ""))[:400],
                    "patch": {
                        "path": ex.get("patch", {}).get("path", ""),
                        "why": str(ex.get("patch", {}).get("why", ""))[:200],
                    },
                }
            )

        user_prompt = PROMPT_USER_FMT.format(
            code=0,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            ctx_json=json.dumps(ctx, ensure_ascii=False)[:CTX_MAX_BYTES],
            fingerprints_json=json.dumps(fps, ensure_ascii=False),
            fewshots_json=json.dumps(compact_fs, ensure_ascii=False),
            allowed_dirs=list(ALLOWED_DIRS),
        )

        proposal = call_model(user_prompt)
        reason = proposal.get("reason", "")
        patch_list = proposal.get("patches", [])
        print(f"[model] reason: {reason}")
        print(f"[model] num patches: {len(patch_list)}")

        valid, errs = validate_patches(patch_list, required_tokens, allowed_paths=trace_allowlist)
        if errs:
            print("! patch validation errors:")
            for e in errs:
                print("  -", e)
        if not valid:
            print("No valid patches; stopping.")
            log_metrics(
                {
                    "ts": int(time.time()),
                    "iter": it,
                    "result": "NO_VALID_PATCH",
                    "model": MODEL,
                    "errors": errs[-10:],
                }
            )
            sys.exit(2)

        # ===== 回帰ゲート：適用 → 整形 → 差分テスト → 失敗ならロールバック =====
        applied = apply_patches_with_backups(valid)
        try:
            format_code()

            # 差分テスト
            target_tests = detect_changed_tests_from_patches(valid)
            start_ts3 = time.time()
            res_diff = run_pytest(light=True, target_tests=target_tests or None)
            diff_elapsed = time.time() - start_ts3

            if not res_diff.ok:
                print("⚠️ Diff tests still failing; rolling back this iteration.")
                log_metrics(
                    {
                        "ts": int(time.time()),
                        "iter": it,
                        "result": "DIFF_FAIL",
                        "model": MODEL,
                        "patch_count": len(valid),
                        "diff_elapsed_sec": round(diff_elapsed, 3),
                        "target_tests": target_tests,
                    }
                )
                rollback_files(applied)
                continue

            # 軽テスト全体
            res_light2 = run_pytest(light=True)
            if not res_light2.ok:
                print("⚠️ Light tests failed after patch; rolling back.")
                log_metrics(
                    {
                        "ts": int(time.time()),
                        "iter": it,
                        "result": "LIGHT_FAIL",
                        "model": MODEL,
                        "patch_count": len(valid),
                    }
                )
                rollback_files(applied)
                continue

            # 重テスト（必要なら）
            green = True
            if LIGHT_FIRST:
                res_heavy2 = run_pytest(light=False)
                if not res_heavy2.ok:
                    print("⚠️ Heavy tests failed after patch; rolling back.")
                    log_metrics(
                        {
                            "ts": int(time.time()),
                            "iter": it,
                            "result": "HEAVY_FAIL",
                            "model": MODEL,
                            "patch_count": len(valid),
                        }
                    )
                    rollback_files(applied)
                    green = False

            if not green:
                continue

            # ここまで来たら成功：バックアップ掃除＆コミット
            finalize_backups(applied)
            if GIT_COMMIT:
                git_commit("autofix: apply model patches (green)")

            print("✅ GREEN — all tests passed after patch.")
            log_metrics(
                {
                    "ts": int(time.time()),
                    "iter": it,
                    "result": "GREEN_AFTER_PATCH",
                    "model": MODEL,
                    "patch_count": len(valid),
                }
            )
            return

        except Exception as e:
            print(f"⚠️ Exception during apply/test: {e}; rolling back.")
            rollback_files(applied)
            continue

    print("🛑 Iteration budget exceeded without turning GREEN.")
    log_metrics(
        {"ts": int(time.time()), "iter": MAX_ITERS, "result": "BUDGET_EXCEEDED", "model": MODEL}
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
