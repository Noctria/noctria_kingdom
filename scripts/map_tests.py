#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
map_tests.py
  - allowed_files.txt から関連テストを推定し tests_map.json を出力
  - 改良点:
      * キーワード拡張: パス要素, stem のスネーク分割, dotted module, ソースの関数/クラス名(AST)
      * フォールバック: マッチ0件なら全テストから上位Nを採用
Usage:
  python scripts/map_tests.py \
    --allow codex_reports/context/allowed_files.txt \
    --out   codex_reports/context/tests_map.json \
    --top   12
"""

from __future__ import annotations
from pathlib import Path
import argparse, json, os, re, subprocess, sys, ast
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]


# ---------------- helpers ----------------
def read_allowed(p: Path) -> list[str]:
    if not p.exists():
        return []
    return [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _snake_tokens(s: str) -> list[str]:
    toks = []
    for part in re.split(r"[_\.-]+", s):
        part = part.strip()
        if len(part) >= 3:
            toks.append(part)
    return toks


def _ast_symbols(py_path: Path) -> list[str]:
    """source から関数/クラス名を抽出（短すぎは除外）"""
    try:
        src = py_path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        names = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if len(node.name) >= 3:
                    names.append(node.name)
        return names
    except Exception:
        return []


def derive_keywords(allowed_paths: list[str]) -> list[str]:
    """
    キーワード拡張:
      - ファイル名 stem / そのスネーク分割
      - dotted module 名（src相当を.に）
      - パス要素（末尾2〜3階層）
      - ソースの関数/クラス名(AST)
    """
    kws = set()
    for rel in allowed_paths:
        rel = rel.replace("\\", "/")
        p = ROOT / rel if not rel.startswith("/") else Path(rel)
        stem = Path(rel).stem
        # stem と分割
        if len(stem) >= 3:
            kws.add(stem)
        for tok in _snake_tokens(stem):
            kws.add(tok)
        # dotted module っぽい
        dotted = rel
        for prefix in ("src/", "./"):
            if dotted.startswith(prefix):
                dotted = dotted[len(prefix) :]
        dotted = dotted[:-3] if dotted.endswith(".py") else dotted
        if dotted:
            dotted = dotted.replace("/", ".")
            if len(dotted) >= 3:
                kws.add(dotted)
        # パス要素(末尾2〜3階層)
        parts = [x for x in rel.split("/") if x]
        for tail in parts[-3:]:
            if tail.endswith(".py"):
                tail = tail[:-3]
            if len(tail) >= 3:
                kws.add(tail)
            for tok in _snake_tokens(tail):
                kws.add(tok)
        # ASTシンボル
        if p.suffix == ".py" and p.exists():
            for sym in _ast_symbols(p):
                kws.add(sym)
    # 3文字未満は除外
    return [k for k in kws if len(k) >= 3]


def collect_tests_via_pytest() -> list[str]:
    """
    pytest -q --collect-only の出力から nodeid を収集。
    出ない環境では tests/**/*.py を列挙。
    """
    nodeids: list[str] = []
    try:
        out = subprocess.run(
            ["pytest", "-q", "--collect-only"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        for ln in (out.stdout or "").splitlines():
            ln = ln.strip()
            if ln.startswith("tests/") and ("::" in ln):
                nodeids.append(ln)
    except FileNotFoundError:
        pass

    if not nodeids:
        # 最低限、テストファイルは拾っておく
        for p in ROOT.glob("tests/**/*.py"):
            rel = p.relative_to(ROOT).as_posix()
            nodeids.append(rel)

    # 一意化
    seen = set()
    uniq = []
    for n in nodeids:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def score_tests(nodeids: list[str], keywords: list[str]) -> list[tuple[str, int]]:
    """
    テスト本文に対する素朴スコア:
      +2: ファイル名stemがキーワードに一致
      +count: 本文にキーワード出現
    """
    scores: dict[str, int] = defaultdict(int)
    kw_low = [k.lower() for k in keywords]
    for node in nodeids:
        test_path = node.split("::", 1)[0]
        p = ROOT / test_path
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
        low = text.lower()
        base = p.stem.lower()
        if base in kw_low:
            scores[node] += 2
        for k in kw_low:
            if not k:
                continue
            cnt = low.count(k)
            if cnt:
                scores[node] += cnt
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked


def write_tests_map(out_path: Path, ranked: list[tuple[str, int]], top: int, debug: dict):
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    selected = [n for n, _ in ranked[:top]] if ranked else []
    data = {
        "generated_by": "scripts/map_tests.py",
        "top": top,
        "selected": selected,
        "ranked": ranked[: max(top, 50)],  # 大きすぎないよう軽く制限
        "debug": debug,
    }
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        rel = out_path.relative_to(ROOT)
    except Exception:
        rel = out_path
    print(f"+ wrote {rel} ({len(selected)} tests)")


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow", default=str(ROOT / "codex_reports/context/allowed_files.txt"))
    ap.add_argument("--out", default=str(ROOT / "codex_reports/context/tests_map.json"))
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    allow = Path(args.allow)
    outp = Path(args.out)

    allowed_paths = read_allowed(allow)
    keywords = derive_keywords(allowed_paths)
    nodeids = collect_tests_via_pytest()
    ranked = score_tests(nodeids, keywords)

    debug = {
        "allowed_count": len(allowed_paths),
        "keywords": keywords[:50],
        "all_tests_found": len(nodeids),
        "ranked_nonzero": sum(1 for _, s in ranked if s > 0),
    }

    # フォールバック: マッチ0件なら全テストから上位Nを採用
    if not ranked or all(s == 0 for _, s in ranked):
        print("WARN: no related tests matched keywords → fallback to all tests (score=0)")
        ranked = [(n, 0) for n in nodeids]

    write_tests_map(outp, ranked, args.top, debug)


if __name__ == "__main__":
    main()
