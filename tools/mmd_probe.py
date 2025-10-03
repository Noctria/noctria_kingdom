#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

ARROWS = [
    '-->', '---', '-.->', '==>', '--', '--o', 'o--', '--x', 'x--',
    '->',  # 念のため
    '→', '⇒', '⟶', '⟹', '➔', '➤', '⟶', '⟿', '↦', '⤏',  # Unicode系
]
PAT = [(a, re.compile(re.escape(a))) for a in ARROWS]

def main(path: str, sample_each=5):
    text = Path(path).read_text(encoding='utf-8', errors='ignore').splitlines()
    counts = {a:0 for a,_ in PAT}
    samples = {a:[] for a,_ in PAT}
    total_arrow_lines = 0
    for ln in text:
        core = ln.split('%%',1)[0]
        if not core.strip(): continue
        hit_any = False
        for a, rgx in PAT:
            if rgx.search(core):
                counts[a]+=1
                if len(samples[a]) < sample_each:
                    samples[a].append(core.strip()[:240])
                hit_any = True
        if hit_any: total_arrow_lines += 1
    print('[probe] lines with any-arrow:', total_arrow_lines)
    for a in ARROWS:
        if counts[a]:
            print(f'  {a:6} : {counts[a]}')
            for s in samples[a]:
                print('    -', s)
    # 追加で :::class と class 行の統計
    c_inline = sum(1 for ln in text if ':::' in ln)
    c_class  = sum(1 for ln in text if ln.strip().startswith('class '))
    print(f'[probe] inline ::: count: {c_inline}, class-line count: {c_class}')

if __name__ == '__main__':
    import sys
    if len(sys.argv)<2:
        print('Usage: python tools/mmd_probe.py <path.mmd>')
        raise SystemExit(2)
    main(sys.argv[1])
