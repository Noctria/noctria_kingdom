# codex/run_codex_cycle.py
import subprocess
import json
from pathlib import Path
import datetime

REPORT_DIR = Path("codex_reports")
REPORT_DIR.mkdir(exist_ok=True)
JSON_FILE = REPORT_DIR / "latest_codex_report.json"
MD_FILE = REPORT_DIR / "latest_codex_cycle.md"

def run_pytest_with_report():
    cmd = [
        "pytest",
        "-q",
        "tests",
        "--json-report",
        f"--json-report-file={JSON_FILE}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode

def generate_md_report(returncode: int):
    if not JSON_FILE.exists():
        MD_FILE.write_text("## Codex Cycle Report\n(no JSON report generated)\n")
        return

    data = json.loads(JSON_FILE.read_text())
    summary = data.get("summary", {})
    tests = data.get("tests", [])

    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)

    lines = []
    lines.append("## Codex Cycle Report")
    lines.append(f"- datetime: {datetime.datetime.now().isoformat()}")
    lines.append(f"- returncode: {returncode}")
    lines.append(f"- total: {total}, passed: {passed}, failed: {failed}, skipped: {skipped}")
    lines.append("")

    lines.append("### Tests executed")
    for t in tests:
        outcome = t.get("outcome")
        symbol = "✅" if outcome == "passed" else "❌" if outcome == "failed" else "⚠️"
        lines.append(f"- {t.get('nodeid')} {symbol}")
    lines.append("")

    if failed > 0:
        lines.append("### Failures")
        for t in tests:
            if t.get("outcome") == "failed":
                nodeid = t.get("nodeid")
                msg = t.get("longrepr", "")
                short_msg = "\n".join(msg.splitlines()[:5])  # 最初の数行だけ抜粋
                lines.append(f"- **{nodeid}**\n```\n{short_msg}\n```")
        lines.append("\n❌ Some tests failed. Next step: generate patch proposal.")

    else:
        lines.append("✅ All selected tests passed.")

    MD_FILE.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    rc = run_pytest_with_report()
    generate_md_report(rc)
    print("== Codex cycle complete ==")
    print(f"Report: {MD_FILE}")
