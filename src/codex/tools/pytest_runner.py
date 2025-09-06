# codex/tools/pytest_runner.py
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import os


def run_pytest(
    targets: List[str],
    *,
    json_report: bool = True,
    json_path: Path = Path("codex_reports/tmp.json"),
    extra_env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    """
    pytest を実行して (returncode, stdout, stderr) を返す。
    - json_report=True のとき、pytest-json-report を強制ロードして JSON を出力。
    """
    # ベースコマンド
    cmd = [sys.executable, "-m", "pytest", "-q"]

    # JSON レポートを有効化する場合、プラグインを明示ロード
    env = os.environ.copy()
    if json_report:
        # オートロードが無効でもプラグインを読み込む
        cmd += ["-p", "pytest_jsonreport", "--json-report", f"--json-report-file={str(json_path)}"]
        # それでも環境側で抑止される可能性に備え、環境変数を解除/上書き
        env.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)

    if extra_env:
        env.update(extra_env)

    # 対象のテストを追加
    cmd += targets

    # 実行
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return proc.returncode, proc.stdout, proc.stderr
