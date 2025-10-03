# src/codex/tools/autofix_gpt_commit_loop.py
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


def run(cmd: List[str] | str, cwd: str | None = None) -> Tuple[int, str, str]:
    """Run a shell command and return (rc, stdout, stderr)."""
    if isinstance(cmd, str):
        shell = True
        cmd_display = cmd
    else:
        shell = False
        cmd_display = " ".join(shlex.quote(c) for c in cmd)

    print(f"[run] {cmd_display}")
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        shell=shell,
        text=True,
        capture_output=True,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode, proc.stdout, proc.stderr


def ensure_module_importable(module: str) -> None:
    """Helpful message if a required module isn't importable on runner."""
    try:
        __import__(module)
    except Exception:
        print(
            f"[hint] Python module '{module}' not importable. If this is a package, "
            f"ensure your runner environment installs it (e.g., pip install -e .)."
        )


def resolve_paths(paths: Iterable[str], globs: Iterable[str]) -> List[Path]:
    """Resolve a list of concrete paths plus glob patterns into unique file Paths."""
    out: list[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.exists():
            out.append(pp)
    for g in globs:
        for pp in Path(".").glob(g):
            if pp.is_file():
                out.append(pp)
    # unique & sort
    uniq = sorted({p.resolve() for p in out})
    return uniq


def run_ruff_check(targets: List[Path]) -> int:
    if not targets:
        return 0
    cmd = ["ruff", "check", *[str(p) for p in targets]]
    rc, _, _ = run(cmd)
    return rc


def run_auto_fix_agent(
    targets: List[Path], use_gpt: bool, fix_rounds: int, ruff_extra: str | None
) -> int:
    """Call our auto_fix_agent which can do rule-based + GPT escalations."""
    ensure_module_importable("src.codex.tools.auto_fix_agent")
    cmd = [
        sys.executable,
        "-m",
        "src.codex.tools.auto_fix_agent",
        "--paths",
        *[str(p) for p in targets],
        "--fix-rounds",
        str(fix_rounds),
    ]
    if use_gpt:
        cmd.append("--use-gpt")
    if ruff_extra:
        cmd.extend(["--ruff-extra", ruff_extra])
    rc, _, _ = run(cmd)
    return rc


def run_pytest(pytest_args: List[str] | None) -> int:
    """Run pytest with given args; default is a quiet, short run."""
    args = pytest_args or ["-q", "-k", "not longrun and not slow"]
    cmd = ["pytest", *args]
    rc, _, _ = run(cmd)
    return rc


def git_current_branch() -> str:
    rc, out, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if rc == 0:
        return out.strip()
    return ""


def git_changed_files(rel_to_repo: bool = True) -> List[str]:
    """Return list of changed (staged/unstaged) files according to git."""
    rc, out, _ = run(["git", "status", "--porcelain"])
    if rc != 0:
        return []
    changed: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        # format: XY <path>
        path = line[3:]
        if rel_to_repo:
            changed.append(path)
        else:
            changed.append(str(Path(path).resolve()))
    return changed


def git_stage(files: Iterable[Path]) -> None:
    paths = [str(p) for p in files]
    if not paths:
        return
    run(["git", "add", *paths])


def git_commit(message: str) -> bool:
    rc, out, _ = run(["git", "commit", "-m", message])
    if rc != 0:
        print("[git] nothing committed (maybe no changes?)")
        return False
    print(out)
    return True


def git_create_switch_branch(branch: str) -> None:
    cur = git_current_branch()
    if cur == branch:
        return
    # try switch
    rc, _, _ = run(["git", "switch", branch])
    if rc == 0:
        return
    # create
    run(["git", "switch", "-c", branch])


def git_push(branch: str, set_upstream: bool = True) -> None:
    if set_upstream:
        run(["git", "push", "-u", "origin", branch])
    else:
        run(["git", "push", "origin", branch])


def filter_commit_candidates(all_changed: List[str], allow_globs: List[str]) -> List[str]:
    """Keep only files matching allow globs; if no allow globs, keep all_changed."""
    if not allow_globs:
        return all_changed
    allow: set[Path] = set()
    for g in allow_globs:
        for p in Path(".").glob(g):
            allow.add(p.resolve())
    picked: list[str] = []
    for rel in all_changed:
        p = Path(rel).resolve()
        if p in allow:
            picked.append(rel)
    return picked


def write_run_report(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[warn] failed to write report {path}: {e}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Autofix loop: Ruff -> auto_fix_agent (rule/GPT) -> Ruff -> pytest -> optional git commit/push."
    )
    parser.add_argument(
        "--paths", nargs="*", default=[], help="Explicit target paths (files/dirs)."
    )
    parser.add_argument(
        "--globs",
        nargs="*",
        default=[],
        help="Glob patterns to expand into files (e.g., 'tests/**/*.py').",
    )
    parser.add_argument("--max-rounds", type=int, default=3, help="Max iterations of the loop.")
    parser.add_argument(
        "--use-gpt",
        action="store_true",
        help="Escalate unresolved Ruff diagnostics to GPT in auto_fix_agent.",
    )
    parser.add_argument(
        "--fix-rounds",
        type=int,
        default=2,
        help="Internal fix rounds to pass to auto_fix_agent.",
    )
    parser.add_argument(
        "--ruff-extra",
        type=str,
        default=None,
        help="Extra args to pass to ruff (e.g., '--ignore E501').",
    )

    parser.add_argument(
        "--pytest",
        dest="use_pytest",
        action="store_true",
        help="Run pytest in the loop.",
    )
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        help="Args passed to pytest after '--'.",
    )

    parser.add_argument(
        "--git-commit",
        action="store_true",
        help="Commit fixed files at the end if Ruff & (optionally) pytest pass.",
    )
    parser.add_argument(
        "--git-push", action="store_true", help="Push the commit to origin/<branch>."
    )
    parser.add_argument(
        "--git-branch",
        type=str,
        default="adopt/autofix-bot",
        help="Branch to commit to (will be created/switch if needed).",
    )
    parser.add_argument(
        "--allow-commit-globs",
        nargs="*",
        default=["tests/**/*.py", "src/**/*.py"],
        help="Only commit files matching these globs.",
    )
    parser.add_argument(
        "--report-json",
        type=str,
        default="src/codex_reports/autofix/last_run.json",
        help="Where to save a small run report.",
    )
    args = parser.parse_args()

    # Resolve targets
    targets = resolve_paths(args.paths, args.globs)
    if not targets:
        print("[exit] No target files. Use --paths or --globs.")
        return 2

    print("=== Autofix Loop ===")
    print(f"- targets: {len(targets)} files")
    for p in targets[:12]:
        print("  •", p)
    if len(targets) > 12:
        print(f"  … and {len(targets) - 12} more")

    # Loop
    final_ruff_rc: int = 1
    final_pytest_rc: int = 0
    rounds = max(1, args.max_rounds)

    # Make sure ruff & pytest are on PATH (give hints if not)
    rc, _, _ = run(["ruff", "--version"])
    if rc != 0:
        print("[error] Ruff not found. Install with: pip install ruff", file=sys.stderr)
        return 2
    if args.use_pytest:
        rc, _, _ = run(["pytest", "--version"])
        if rc != 0:
            print(
                "[error] pytest not found. Install with: pip install pytest",
                file=sys.stderr,
            )
            return 2

    # Try import auto_fix_agent so users get a helpful hint if missing
    ensure_module_importable("src.codex.tools.auto_fix_agent")

    for i in range(1, rounds + 1):
        print(f"\n--- Round {i}/{rounds} ---")

        # 1) Try rule-based + GPT-escalation fixes
        _ = run_auto_fix_agent(
            targets,
            use_gpt=args.use_gpt,
            fix_rounds=args.fix_rounds,
            ruff_extra=args.ruff_extra,
        )

        # 2) Ruff check
        final_ruff_rc = run_ruff_check(targets)
        if final_ruff_rc == 0:
            print("[ruff] ✅ clean")
        else:
            print("[ruff] ❌ issues remain")

        # 3) Optional pytest
        if args.use_pytest:
            pytest_args = None
            # argparse.REMAINDER puts everything after '--' into pytest_args
            if args.pytest_args:
                pytest_args = args.pytest_args
            final_pytest_rc = run_pytest(pytest_args)
        else:
            final_pytest_rc = 0

        # Stop if both passed
        if final_ruff_rc == 0 and final_pytest_rc == 0:
            print(f"[round {i}] ✅ success; stopping loop.")
            break
        else:
            print(f"[round {i}] continuing… (ruff={final_ruff_rc}, pytest={final_pytest_rc})")

    # Report
    report = {
        "targets": [str(p) for p in targets],
        "rounds": rounds,
        "ruff_ok": (final_ruff_rc == 0),
        "pytest_enabled": args.use_pytest,
        "pytest_ok": (final_pytest_rc == 0),
    }
    write_run_report(Path(args.report_json), report)

    # Optionally commit & push when green
    if args.git_commit and final_ruff_rc == 0 and final_pytest_rc == 0:
        # Ensure branch
        git_create_switch_branch(args.git_branch)

        # Stage only allowed changes
        changed = git_changed_files(rel_to_repo=True)
        if changed:
            allowed = filter_commit_candidates(changed, args.allow_commit_globs)
        else:
            allowed = []

        if not allowed:
            print("[git] nothing to commit in allowed globs; skipping commit.")
        else:
            to_stage = [Path(p) for p in allowed]
            git_stage(to_stage)
            committed = git_commit("style: autofix via Ruff + GPT loop")
            if committed and args.git_push:
                git_push(args.git_branch, set_upstream=True)

    # Exit code mirrors lint/pytest status: 0 if both ok (or pytest disabled), else 1
    ok = (final_ruff_rc == 0) and (final_pytest_rc == 0)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
