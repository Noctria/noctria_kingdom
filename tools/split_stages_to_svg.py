from pathlib import Path
import re
import subprocess

SRC = Path("data/repo_dependencies_py_only_tagged.mmd")
OUT = Path("codex_reports/graphs/pages_svg")
OUT.mkdir(parents=True, exist_ok=True)

node_re = re.compile(r"^\s*([A-Za-z0-9_./:\-]+)\s*\[(.*?)\]\s*$")
class_re = re.compile(r"^\s*class\s+([A-Za-z0-9_./:\-]+)\s+([A-Za-z0-9_,\-]+);")
lines = SRC.read_text(encoding="utf-8").splitlines()

nodes, classes = {}, {}
for ln in lines:
    m = node_re.match(ln)
    if m:
        nodes[m.group(1)] = ln
    m = class_re.match(ln)
    if m and not m.group(1).startswith("legend_"):
        nid = m.group(1)
        for c in m.group(2).split(","):
            c = c.strip()
            if c in {
                "collect",
                "analyze",
                "plan",
                "backtest",
                "forwardtest",
                "fintokei_check",
                "mt5_order",
                "settlement",
                "result_analyze",
                "merge_info",
                "replanning",
            }:
                classes.setdefault(c, set()).add(nid)

# Mermaid設定（無ければ作る）
cfg = Path("tools/mermaid_config.json")
if not cfg.exists():
    cfg.write_text(
        '{"maxTextSize":2000000,"securityLevel":"loose","flowchart":{"htmlLabels":false,"useMaxWidth":true,"curve":"basis"}}',
        encoding="utf-8",
    )

for st, mem in classes.items():
    mem = sorted(mem)
    sub = OUT / f"{st}_py_only.mmd"
    out_lines = ["flowchart TB"]
    for n in mem:
        if n in nodes:
            out_lines.append(nodes[n])
        else:
            # ノード行が無ければプレースホルダ
            out_lines.append(f'{n}["{n}"]')
    sub.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    subprocess.run(
        ["mmdc", "-i", str(sub), "-o", str(OUT / f"{st}.svg"), "-b", "transparent", "-c", str(cfg)],
        check=True,
    )
    print(f"{st}: {len(mem)} -> {OUT/st}.svg")
