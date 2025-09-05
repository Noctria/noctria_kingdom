# noctria_gui/routes/strategy_detail.py
#!/usr/bin/env python3
# coding: utf-8
"""
📘 Strategy Detail Route (v3.3 safe + module fallback)
- 指定戦略の PDCA 推移・トレンド/分布・履歴を可視化
- 依存が未配備でも 500 にせずフォールバック
  * 統計ログが無い場合でも、戦略ファイル/モジュールがあれば表示
  * ?raw=1 : JSON 生返却
  * ?safe=1: テンプレ失敗時は簡易HTML（既定ON）
"""

from __future__ import annotations

import importlib
import json
import logging
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger("noctria_gui.strategy_detail")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ------------------------------------------------------------
# パス設定（path_config がなくても動く）
# ------------------------------------------------------------
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parents[2]  # <repo_root>
try:
    from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, DATA_DIR, STRATEGIES_DIR  # type: ignore
except Exception:  # pragma: no cover
    NOCTRIA_GUI_TEMPLATES_DIR = PROJECT_ROOT / "noctria_gui" / "templates"
    DATA_DIR = PROJECT_ROOT / "data"
    STRATEGIES_DIR = PROJECT_ROOT / "src" / "strategies"

STATS_DIR = DATA_DIR / "stats"
router = APIRouter(prefix="/strategies", tags=["strategy-detail"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ------------------------------------------------------------
# 依存サービス（無ければフォールバック）
# ------------------------------------------------------------
def _load_all_statistics_fallback() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not STATS_DIR.exists():
        return out
    for fp in sorted(STATS_DIR.glob("*.json")):
        try:
            text = fp.read_text(encoding="utf-8").strip()
            if not text:
                continue
            if text.lstrip().startswith("["):
                arr = json.loads(text)
                if isinstance(arr, list):
                    out.extend(x for x in arr if isinstance(x, dict))
            else:
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict):
                            out.append(obj)
                    except Exception:
                        continue
        except Exception:
            continue
    return out

try:
    from noctria_gui.services import statistics_service  # type: ignore
    def load_all_statistics() -> List[Dict[str, Any]]:
        try:
            logs = statistics_service.load_all_statistics()
            if logs and is_dataclass(logs[0]):
                return [asdict(x) for x in logs]
            return logs
        except Exception:
            logger.warning("statistics_service.load_all_statistics() 失敗。フォールバックに切替。", exc_info=True)
            return _load_all_statistics_fallback()
except Exception:  # pragma: no cover
    def load_all_statistics() -> List[Dict[str, Any]]:
        return _load_all_statistics_fallback()

# ------------------------------------------------------------
# 表示メトリクス
# ------------------------------------------------------------
DASHBOARD_METRICS: List[Dict[str, Any]] = [
    {"key": "win_rate",      "label": "勝率",    "unit": "%", "dec": 2},
    {"key": "max_drawdown",  "label": "最大DD",  "unit": "%", "dec": 2},
    {"key": "trade_count",   "label": "取引数",  "unit": "回", "dec": 0},
    {"key": "profit_factor", "label": "PF",      "unit": "",  "dec": 2},
]

# ------------------------------------------------------------
# ユーティリティ（%変換・集計）
# ------------------------------------------------------------
def _to_pct_if_ratio(k: str, v: Any) -> Any:
    try:
        fv = float(v)
    except Exception:
        return v
    if k in {"win_rate", "max_drawdown"} and 0.0 <= fv <= 1.0:
        return fv * 100.0
    return fv

def _agg(vals: List[Optional[float]], dec: int) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    xs = [v for v in vals if isinstance(v, (int, float))]
    if not xs:
        return None, None, None
    avg = round(sum(xs) / len(xs), dec)
    return avg, round(max(xs), dec), round(min(xs), dec)

# ------------------------------------------------------------
# ログ→履歴/トレンド/分布 生成
# ------------------------------------------------------------
def _build_history_trend_dist(strategy_name: str, logs: List[Dict[str, Any]]):
    hist = [log for log in logs if log.get("strategy") == strategy_name]
    if not hist:
        return None, None, None

    trend = defaultdict(lambda: defaultdict(list))
    dist = defaultdict(list)

    for log in hist:
        date = (log.get("evaluated_at") or "")[:10]
        for m in DASHBOARD_METRICS:
            k = m["key"]
            v = log.get(k)
            if v is None:
                continue
            v = _to_pct_if_ratio(k, v)
            if date:
                trend[date][k].append(v)
            dist[k].append(v)

    dates = sorted(trend.keys())
    trend_dict: Dict[str, Dict[str, Any]] = {}
    for m in DASHBOARD_METRICS:
        k = m["key"]
        vals: List[Optional[float]] = []
        for d in dates:
            arr = trend[d][k]
            vals.append(round(sum(arr) / len(arr), m["dec"]) if arr else None)
        avg, vmax, vmin = _agg(vals, m["dec"])
        diff = None
        seq = [v for v in vals if v is not None]
        if len(seq) >= 2:
            diff = round(seq[-1] - seq[-2], m["dec"])
        trend_dict[k] = {"labels": dates, "values": vals, "avg": avg, "max": vmax, "min": vmin, "diff": diff}
    return hist, trend_dict, dist

# ------------------------------------------------------------
# モジュール / ファイル フォールバック
# ------------------------------------------------------------
def _strategy_candidates(name: str) -> List[Path]:
    vg = STRATEGIES_DIR / "veritas_generated"
    return [
        vg / f"{name}.py", vg / f"{name}.json",
        STRATEGIES_DIR / f"{name}.py", STRATEGIES_DIR / f"{name}.json",
    ]

def _strategy_exists(name: str) -> bool:
    return any(p.exists() for p in _strategy_candidates(name))

def _import_strategy_module(name: str):
    for mn in (f"strategies.veritas_generated.{name}", f"strategies.{name}"):
        try:
            return importlib.import_module(mn)
        except Exception:
            continue
    return None

def _compute_kpis_from_module(mod) -> Dict[str, Any]:
    # Strategy クラス優先
    for attr in ("Strategy", "strategy",):
        S = getattr(mod, attr, None)
        if S:
            try:
                obj = S() if callable(S) else S
                if hasattr(obj, "compute_kpis"):
                    k = obj.compute_kpis()
                    if is_dataclass(k): k = asdict(k)
                    if not isinstance(k, dict): k = dict(k)
                    return k
            except Exception:
                pass
    # top-level 関数
    for fn_name in ("compute_kpis", "get_kpis", "calc_kpis"):
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            try:
                k = fn()
                if is_dataclass(k): k = asdict(k)
                if not isinstance(k, dict): k = dict(k)
                return k
            except Exception:
                pass
    # run_backtest -> (kpis, trades)
    rb = getattr(mod, "run_backtest", None)
    if callable(rb):
        try:
            ret = rb()
            if isinstance(ret, tuple) and len(ret) >= 1:
                k = ret[0]
                if is_dataclass(k): k = asdict(k)
                if not isinstance(k, dict): k = dict(k)
                return k
        except Exception:
            pass
    # 何もなければ placeholder
    return {"trades": 0, "win_rate": None, "avg_return_pct": None, "pnl_sum_pct": None, "max_drawdown_pct": None, "_note": "module: KPIs unavailable"}

def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# ------------------------------------------------------------
# Route
# ------------------------------------------------------------
@router.get("/detail/{strategy_name}", response_class=HTMLResponse)
async def show_strategy_detail(
    request: Request,
    strategy_name: str,
    trace_id: Optional[str] = Query(None),
    decision_id: Optional[str] = Query(None),
    safe: int = Query(1, description="1=安全モード（テンプレ失敗でも簡易HTMLで返す）"),
    raw: int = Query(0, description="1=JSONで返す"),
):
    logger.info("戦略詳細リクエスト: %s", strategy_name)

    # 1) まず統計ログで探す
    logs: List[Dict[str, Any]] = []
    try:
        logs = load_all_statistics()
    except Exception as e:
        logger.warning("統計ログ読み込み失敗（フォールバック継続）: %s", e, exc_info=True)
        logs = []

    matched_strategy = next((log for log in logs if log.get("strategy") == strategy_name), None)

    # 2) ログになければ、モジュール/ファイルでフォールバック表示
    fallback_used = False
    if not matched_strategy:
        if not _strategy_exists(strategy_name):
            # 本当に何も無ければ 404
            raise HTTPException(status_code=404, detail=f"戦略『{strategy_name}』は見つかりません。")
        # KPI だけでも出す
        mod = _import_strategy_module(strategy_name)
        kpis = {}
        if mod:
            try:
                kpis = _compute_kpis_from_module(mod)
            except Exception:
                kpis = {}
        matched_strategy = {
            "strategy": strategy_name,
            "tags": [],
            "win_rate": kpis.get("win_rate"),
            "max_drawdown": kpis.get("max_drawdown") or kpis.get("max_drawdown_pct"),
            "trade_count": kpis.get("trades") or kpis.get("trade_count"),
            "profit_factor": kpis.get("profit_factor"),
            "kpis": kpis,
            "_source": "module_only",
            "_observed_at": _now_iso(),
        }
        logs = []  # 履歴なし
        fallback_used = True

    # 3) 関連戦略（タグ一致）
    def _find_related_by_tags(all_logs: List[Dict[str, Any]], current_tags: List[str]) -> List[Dict[str, Any]]:
        if not all_logs or not current_tags:
            return []
        rel, seen = [], set()
        for s in all_logs:
            name = s.get("strategy")
            if not name or name == strategy_name or name in seen:
                continue
            tags = s.get("tags") or []
            if any(t in (tags or []) for t in current_tags):
                rel.append(s); seen.add(name)
            if len(rel) >= 4:
                break
        return rel

    current_tags = matched_strategy.get("tags") or []
    related_strategies = _find_related_by_tags(logs, current_tags)

    # 4) 履歴/トレンド/分布
    hist, trend_dict, dist = _build_history_trend_dist(strategy_name, logs)
    if hist is None:
        # 履歴が無い場合は空で返す（フォールバック時も 200 にする）
        hist, trend_dict, dist = [], {}, {}

    # 5) raw=1 なら JSON 返却
    base_payload = {
        "strategy": matched_strategy,
        "related_strategies": related_strategies,
        "dashboard_metrics": DASHBOARD_METRICS,
        "trend_dict": trend_dict,
        "metric_dist": dist,
        "eval_list": sorted(hist, key=lambda x: (x.get("evaluated_at") or ""), reverse=True),
        "trace_id": trace_id,
        "decision_id": decision_id,
        "_fallback_used": fallback_used,
    }
    if raw == 1:
        return JSONResponse(base_payload)

    # 6) テンプレ描画（無ければ簡易HTML）
    tpl_primary = NOCTRIA_GUI_TEMPLATES_DIR / "strategies" / "detail.html"
    tpl_legacy = NOCTRIA_GUI_TEMPLATES_DIR / "strategy_detail.html"
    context = {"request": request, **base_payload}
    tpl_name = "strategies/detail.html" if tpl_primary.exists() else ("strategy_detail.html" if tpl_legacy.exists() else None)

    if tpl_name:
        if safe == 1:
            try:
                return templates.TemplateResponse(tpl_name, context)
            except Exception as e:
                logger.warning("テンプレ描画失敗。簡易HTMLにフォールバック: %s", e, exc_info=True)
                # fallthrough to simple HTML
        else:
            return templates.TemplateResponse(tpl_name, context)

    # 簡易HTMLフォールバック
    simple = f"""
    <html><head><meta charset="utf-8"><title>{strategy_name} - Strategy Detail (safe)</title></head>
    <body>
      <h1>Strategy: {strategy_name}</h1>
      <p>trace_id: { (trace_id or "-") }</p>
      <p>decision_id: { (decision_id or "-") }</p>

      <h2>Overview</h2>
      <pre>{json.dumps(matched_strategy, ensure_ascii=False, indent=2)}</pre>

      <h2>Trends</h2>
      <pre>{json.dumps(trend_dict, ensure_ascii=False, indent=2)}</pre>

      <h2>Distributions</h2>
      <pre>{json.dumps({k:list(map(float, v)) for k,v in (dist or {}).items()}, ensure_ascii=False, indent=2)}</pre>

      <h2>Evaluations</h2>
      <pre>{json.dumps(base_payload["eval_list"], ensure_ascii=False, indent=2)}</pre>

      {"<h2>Related</h2><pre>"+json.dumps(related_strategies, ensure_ascii=False, indent=2)+"</pre>" if related_strategies else ""}
    </body></html>
    """.strip()
    return HTMLResponse(content=simple, status_code=200)
