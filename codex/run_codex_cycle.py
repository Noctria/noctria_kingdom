from __future__ import annotations
import os, sys, yaml
from typing import List
from pathlib import Path

# codex.tools から読み込むように変更
from codex.tools.patch_notes import make_patch_notes


def load_config() -> dict:
    cfg_path = Path("codex_config/agents.yaml")
    if not cfg_path.exists():
        raise SystemExit("codex_config/agents.yaml が見つかりません")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    cfg = load_config()
    phase = cfg.get("phase", "LV1")
    tests_light: List[str] = cfg.get("tests", {}).get("light", [])
    if not tests_light:
        raise SystemExit("tests.light が未設定です")

    notes = make_patch_notes(tests_light)
    out_dir = Path("codex_reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "latest_codex_cycle.md"
    out_file.write_text(notes, encoding="utf-8")

    print("== Codex cycle complete ==")
    print(f"Report: {out_file}")

if __name__ == "__main__":
    main()
