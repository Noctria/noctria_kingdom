#!/usr/bin/env python
from __future__ import annotations

# --- repo ルートを sys.path に追加（どこから実行してもOKにする）---
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import json
import argparse

# 集中パス管理に準拠して import 経路を安定化
from src.core.path_config import ensure_import_path, GOALS_DIR

ensure_import_path()  # PROJECT_ROOT / SRC を sys.path に整える

from src.codex.goals import load_goals, as_jsonable


def main() -> None:
    ap = argparse.ArgumentParser()
    # 既定は集中管理ディレクトリ（<repo>/codex_goals）
    ap.add_argument("--goal-dir", default=str(GOALS_DIR))
    args = ap.parse_args()

    goals = load_goals(args.goal_dir)
    print(json.dumps(as_jsonable(goals), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
