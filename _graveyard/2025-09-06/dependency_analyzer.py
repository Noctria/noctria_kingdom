# tools/dependency_analyzer.py

import os
import re
from collections import defaultdict
from pathlib import Path

TARGET_DIRS = ["veritas", "execution", "tests"]
BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_FILE = BASE_DIR / "docs" / "diagnostics" / "dependency_map.txt"

IMPORT_PATTERN = re.compile(r'^\s*(?:from|import)\s+([\w\.]+)')

def analyze_imports(base_dir: Path, target_dirs: list) -> dict:
    dependencies = defaultdict(set)

    for d in target_dirs:
        target_path = base_dir / d
        if not target_path.exists():
            continue

        for py_file in target_path.rglob("*.py"):
            rel_path = py_file.relative_to(base_dir)
            module_key = str(rel_path)

            with open(py_file, "r", encoding="utf-8") as f:
                for line in f:
                    match = IMPORT_PATTERN.match(line)
                    if match:
                        imported = match.group(1)
                        top_module = imported.split(".")[0]
                        if top_module in ["core", "veritas", "execution", "tests"]:
                            dependencies[module_key].add(top_module)

    return dependencies

def format_dependencies(deps: dict) -> str:
    lines = ["📊 Noctria Kingdom 依存関係診断マップ\n"]
    for module, imports in sorted(deps.items()):
        lines.append(f"📄 {module}")
        for imp in sorted(imports):
            lines.append(f"   └─ 📦 depends on → {imp}")
        lines.append("")  # 空行
    return "\n".join(lines)

def main():
    pr
