#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
map_tests.py
  - allowed_files.txt を読み、関連テストをスコアリングして tests_map.json を出力

Usage:
  python scripts/map_tests.py --allow codex_reports/context/allowed_files.txt --out codex_reports/context/tests_map.json --top 12
"""
from __future__ import annotations
from pathlib import Path
import argparse, json, os, re, subprocess, sys
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]

def read_allowed(p: Path) -> list[str]:
    if not p.exists(): return []
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return lines

def derive_keywords(allowed_paths: list[str]) -> list[str]:
    kws = set()
    for rel in allowed_paths:
        rel = rel.replace("\\","/")
        p = Path(rel)
        if p.suffix == ".py":
            stem = p.stem
            kws.add(stem)
            # module 風も
            try:
                kws.add(str(p.with_suffix("")).replace("/", "."))
            except Exception:
                pass
        # ディレクトリ指定にも対応（最後の名前）
        kws.add(p.name)
    # 短すぎるのは除外
    return [k for k in kws if len(k) >= 3]

def collect_tests_via_pytest() -> list[str]:
    """
    pytest -q --collect-only の出力から tests/...::test_xxx 形式を拾う。
    取りこぼしがある環境向けに、tests/**/*.py を補完として集める。
    """
    nodeids: list[str] = []
    try:
        out = subprocess.run(
            ["pytest", "-q", "--collect-only"],
            cwd=str(ROOT), capture_output=True, text=True, check=False
        )
        for ln in (out.stdout or "").splitlines():
            ln = ln.strip()
            # 典型的な nodeid 形式だけ拾う
            if ln.startswith("tests/") and ("::" in ln):
                nodeids.append(ln)
    except FileNotFoundError:
        pass

    # 補完：tests/**/*.py を nodeid 化（::test_ は後でpytestが解決する想定）
    if not nodeids:
        for p in ROOT.glob("tests/**/*.py"):
            rel = p.relative_to(ROOT).as_posix()
            nodeids.append(rel)
    # 一意に
    seen=set(); uniq=[]
    for n in nodeids:
        if n not in seen:
            seen.add(n); uniq.append(n)
    return uniq

def score_tests(nodeids: list[str], keywords: list[str]) -> list[tuple[str,int]]:
    """
    テストファイル本文に対する素朴な文字列ヒット数でスコアリング。
    """
    scores: dict[str,int] = defaultdict(int)
    for node in nodeids:
        # ファイルパス部分だけ見る
        test_path = node.split("::",1)[0]
        p = ROOT / test_path
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
        low = text.lower()
        base = p.stem.lower()
        # ファイル名ヒントを少し加点
        if base in keywords:
            scores[node] += 2
        # 本文ヒット
        for kw in keywords:
            k = kw.lower()
            if not k: continue
            cnt = low.count(k)
            if cnt: scores[node] += cnt
    # 並び替え
    ranked = sorted(scores.items(), key=lambda kv:(-kv[1], kv[0]))
    return ranked

def write_tests_map(out_path: Path, ranked: list[tuple[str,int]], top: int):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    selected = [n for n,_ in ranked[:top]] if ranked else []
    data = {
        "generated_by": "scripts/map_tests.py",
        "top": top,
        "selected": selected,
        "ranked": ranked,  # 参考用にスコアも残す
    }
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"+ wrote {out_path.relative_to(ROOT)} ({len(selected)} tests)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow", default=str(ROOT/"codex_reports/context/allowed_files.txt"))
    ap.add_argument("--out",   default=str(ROOT/"codex_reports/context/tests_map.json"))
    ap.add_argument("--top",   type=int, default=12)
    args = ap.parse_args()

    allow = Path(args.allow)
    outp  = Path(args.out)
    allowed_paths = read_allowed(allow)
    if not allowed_paths:
        print(f"WARN: allowed_files.txt が空です: {allow}", file=sys.stderr)

    keywords = derive_keywords(allowed_paths)
    nodeids  = collect_tests_via_pytest()
    ranked   = score_tests(nodeids, keywords)
    write_tests_map(outp, ranked, args.top)

if __name__ == "__main__":
    main()
