import os
import re

FOLDER = "./generated_code"
pkgs = set()

pattern = re.compile(r"^\s*import\s+([a-zA-Z0-9_]+)|^\s*from\s+([a-zA-Z0-9_]+)")

for fname in os.listdir(FOLDER):
    if fname.endswith(".py"):
        with open(os.path.join(FOLDER, fname), encoding="utf-8") as f:
            for line in f:
                m = pattern.match(line)
                if m:
                    pkg = m.group(1) or m.group(2)
                    if pkg:
                        pkgs.add(pkg)

# 標準ライブラリ候補を除外（例：os, sys, re などは無視）
std_libs = {
    "os", "sys", "re", "math", "datetime", "time", "random", "json",
    "logging", "itertools", "functools", "collections", "subprocess",
    "pathlib", "typing", "unittest"
}
pkgs = {p for p in pkgs if p not in std_libs}

with open("requirements_autogen.txt", "w") as f:
    for pkg in sorted(pkgs):
        f.write(pkg + "\n")

print("requirements_autogen.txt generated. Install with:")
print("  pip install -r requirements_autogen.txt")
