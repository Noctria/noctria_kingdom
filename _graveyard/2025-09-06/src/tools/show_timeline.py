# ============================================
# File: src/tools/show_timeline.py
# ============================================
"""
CLI: Show Noctria observability timeline & latency

Usage examples:
  # Show recent trace IDs (top 10)
  python -m src.tools.show_timeline --list-traces

  # Show timeline for a specific trace (compact)
  python -m src.tools.show_timeline --trace TID

  # Show timeline with pretty JSON payloads
  python -m src.tools.show_timeline --trace TID --wide

  # Ensure views & show last 14 days latency percentiles
  python -m src.tools.show_timeline --daily-latency --days 14 --refresh-views

Environment:
  NOCTRIA_OBS_PG_DSN (e.g. postgresql://user:pass@localhost:5433/noctria_db)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------
# Import path stabilization
#   - Insert <repo>/src into sys.path so "from plan_data ..." works.
#   - If available, delegate to core.path_config.ensure_import_path().
# ---------------------------------------------------------------------
SRC_DIR = Path(__file__).resolve().parents[1]  # .../<repo>/src
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    # Optional centralized import-path manager
    from core.path_config import ensure_import_path  # type: ignore
    ensure_import_path()
except Exception:
    pass

# We reuse observability helpers (for ensure_* only).
from plan_data.observability import ensure_tables, ensure_views, refresh_materialized  # type: ignore


# ---------------------------------------------------------------------
# Minimal Postgres driver loader (psycopg2 -> psycopg)
# ---------------------------------------------------------------------
@dataclass
class _Driver:
    mod: Any
    kind: str  # "psycopg2" or "psycopg"


_DRIVER: Optional[_Driver] = None


def _import_driver() -> _Driver:
    global _DRIVER
    if _DRIVER is not None:
        return _DRIVER
    try:
        import psycopg2 as _psycopg2  # type: ignore
        _DRIVER = _Driver(_psycopg2, "psycopg2")
        return _DRIVER
    except ModuleNotFoundError:
        pass
    try:
        import psycopg as _psycopg  # type: ignore
        _DRIVER = _Driver(_psycopg, "psycopg")
        return _DRIVER
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Neither 'psycopg2' nor 'psycopg' installed. "
            "Install one of:\n"
            "  pip install 'psycopg2-binary>=2.9.9,<3.0'\n"
            "  # or\n"
            "  pip install 'psycopg[binary]>=3.1,<3.2'"
        ) from e


def _get_conn(dsn: str):
    drv = _import_driver()
    if drv.kind == "psycopg2":
        conn = drv.mod.connect(dsn)
        conn.autocommit = True
    else:
        conn = drv.mod.connect(dsn, autocommit=True)
    return conn


# ---------------------------------------------------------------------
# DSN
# ---------------------------------------------------------------------
def _get_dsn(env_dsn: Optional[str], cli_dsn: Optional[str]) -> str:
    dsn = cli_dsn or env_dsn or os.getenv("NOCTRIA_OBS_PG_DSN")
    if not dsn:
        raise SystemExit(
            "ERROR: PostgreSQL DSN is not provided. "
            "Set NOCTRIA_OBS_PG_DSN or pass --dsn."
        )
    return dsn


# ---------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------
def _fetchall(dsn: str, sql: str, params: Optional[Sequence[Any]] = None) -> list:
    conn = _get_conn(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------
def _json_str(x: Any) -> str:
    if isinstance(x, (str, bytes)):
        try:
            # Try to pretty if it's a JSON string already
            return json.dumps(json.loads(x), ensure_ascii=False)
        except Exception:
            return x.decode() if isinstance(x, bytes) else x
    return json.dumps(x, ensure_ascii=False)


def _json_pretty(x: Any) -> str:
    if isinstance(x, (str, bytes)):
        try:
            return json.dumps(json.loads(x), ensure_ascii=False, indent=2, sort_keys=True)
        except Exception:
            return x.decode() if isinstance(x, bytes) else x
    return json.dumps(x, ensure_ascii=False, indent=2, sort_keys=True)


def _truncate(s: str, n: int = 96) -> str:
    return s if len(s) <= n else (s[: n - 1] + "…")


def _print_table(rows: Iterable[Sequence[Any]], headers: Sequence[str]) -> None:
    rows = list(rows)
    cols = len(headers)
    widths = [len(h) for h in headers]
    str_rows: List[List[str]] = []
    for r in rows:
        sr: List[str] = []
        for i in range(cols):
            v = r[i]
            if isinstance(v, datetime):
                s = v.isoformat(sep=" ", timespec="seconds")
            elif i == cols - 1:  # payload-ish last column might be JSON
                s = _truncate(_json_str(v), 100)
            else:
                s = "" if v is None else str(v)
            widths[i] = max(widths[i], len(s))
            sr.append(s)
        str_rows.append(sr)

    # header
    line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep = "-+-".join("-" * widths[i] for i in range(cols))
    print(line)
    print(sep)
    for sr in str_rows:
        print(" | ".join(sr[i].ljust(widths[i]) for i in range(cols)))


# ---------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------
def action_list_traces(dsn: str, limit: int) -> None:
    sql = """
    SELECT trace_id, MAX(ts) AS last_ts, COUNT(*) AS events
    FROM obs_trace_timeline
    GROUP BY trace_id
    ORDER BY last_ts DESC
    LIMIT %s;
    """
    rows = _fetchall(dsn, sql, (limit,))
    _print_table(rows, headers=["trace_id", "last_ts", "events"])


def action_show_timeline(dsn: str, trace_id: str, wide: bool, limit: Optional[int]) -> None:
    sql = """
    SELECT ts, kind, action, payload
      FROM obs_trace_timeline
     WHERE trace_id = %s
     ORDER BY ts
    """
    if limit and limit > 0:
        sql += " LIMIT %s"
        rows = _fetchall(dsn, sql, (trace_id, limit))
    else:
        rows = _fetchall(dsn, sql, (trace_id,))

    if not wide:
        _print_table(rows, headers=["ts", "kind", "action", "payload"])
        return

    # wide: pretty-print each row with JSON payload
    for (ts, kind, action, payload) in rows:
        print(f"- ts: {ts}")
        print(f"  kind: {kind}")
        print(f"  action: {action}")
        print("  payload:")
        print("\n".join("    " + ln for ln in _json_pretty(payload).splitlines()))
        print()


def action_daily_latency(dsn: str, days: int) -> None:
    sql = """
    SELECT day, p50_ms, p90_ms, p95_ms, max_ms, traces
      FROM obs_latency_daily
     ORDER BY day DESC
     LIMIT %s;
    """
    rows = _fetchall(dsn, sql, (days,))
    _print_table(rows, headers=["day", "p50_ms", "p90_ms", "p95_ms", "max_ms", "traces"])


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Show obs timeline / latency")
    p.add_argument("--dsn", default=None, help="PostgreSQL DSN (overrides NOCTRIA_OBS_PG_DSN)")
    p.add_argument("--refresh-views", action="store_true", help="Ensure/refresh timeline & latency views before querying")
    sub = p.add_subparsers(dest="cmd")

    s_list = sub.add_parser("list", help="List recent trace IDs")
    s_list.add_argument("--limit", type=int, default=10)

    s_tl = sub.add_parser("timeline", help="Show timeline for a trace_id")
    s_tl.add_argument("--trace", "-t", required=True)
    s_tl.add_argument("--wide", action="store_true", help="Pretty-print payload JSON")
    s_tl.add_argument("--limit", type=int, default=0, help="Limit rows (0=all)")

    s_lat = sub.add_parser("daily-latency", help="Show daily latency percentiles")
    s_lat.add_argument("--days", type=int, default=14)

    # Short aliases with no subcommand:
    p.add_argument("--list-traces", action="store_true", help="[alias] list recent trace IDs")
    p.add_argument("--trace", "-t", help="[alias] show timeline for trace_id")
    p.add_argument("--wide", action="store_true", help="[alias] with --trace, pretty payload")
    p.add_argument("--days", type=int, help="[alias] with --daily-latency")
    p.add_argument("--daily-latency", action="store_true", help="[alias] show daily latency")

    return p.parse_args()


def main() -> None:
    args = parse_args()
    dsn = _get_dsn(env_dsn=None, cli_dsn=args.dsn)

    # Ensure base tables exist (harmless if already there)
    ensure_tables()
    if args.refresh_views:
        ensure_views()
        refresh_materialized()

    # alias routing
    if args.list_traces and not args.cmd:
        return action_list_traces(dsn, limit=10)
    if args.daily_latency and not args.cmd:
        ensure_views()
        return action_daily_latency(dsn, days=args.days or 14)
    if args.trace and not args.cmd:
        ensure_views()
        return action_show_timeline(dsn, trace_id=args.trace, wide=args.wide, limit=None)

    # subcommands
    if args.cmd == "list":
        return action_list_traces(dsn, limit=args.limit)
    elif args.cmd == "timeline":
        ensure_views()
        return action_show_timeline(dsn, trace_id=args.trace, wide=args.wide, limit=args.limit if args.limit > 0 else None)
    elif args.cmd == "daily-latency":
        ensure_views()
        return action_daily_latency(dsn, days=args.days)
    else:
        # default help
        print(__doc__.strip())


if __name__ == "__main__":
    main()
