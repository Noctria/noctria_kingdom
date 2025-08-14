# noctria_gui/routes/strategy_detail.py
#!/usr/bin/env python3
# coding: utf-8
"""
📘 Strategy Detail Route (v3.2 safe)
- 指定戦略の PDCA 推移・指標トレンド/分布・履歴を可視化
- 依存（templates / services）が未配備でも 500 にせずフォールバック
  - ?raw=1  : JSON生出力
  - ?safe=1 : テンプレ失敗時は簡易HTMLで返す（既定ON）
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# ------------------------------------------------------------
# ロギング
# ------------------------------------------------------------
logger = logging.getLogger("noctria_gui.strategy_detail")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# ------------------------------------------------------------
# パス設定（path_config がなくても動作）
# ------------------------------------------------------------
_THIS = Path(__file__).resolve()
PROJECT_ROOT = _THIS.parents[2]  # <repo_root>

try:
    from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, DATA_DIR  # type: ignore
except Exception:  # pragma: no cover
    NOCTRIA_GUI_TEMPLATES_DIR = PROJECT_ROOT / "noctria_gui" / "templates"
    DATA_DIR = PROJECT_ROOT / "data"

STATS_DIR = DATA_DIR / "stats"

router = APIRouter(prefix="/strategies", tags=["strategy-detail"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

# ------------------------------------------------------------
# 依存サービス（未配備でもフォールバック）
# ------------------------------------------------------------
def _load_all_statistics_fallback() -> List[Dict[str, Any]]:
    """data/stats/ 配下の *.json（配列 or 1行1JSON）を素直に読み込むフォールバック。"""
    out: List[Dict[str, Any]] = []
    if not STATS_DIR.exists():
        return out

    for fp in sorted(STATS_DIR.glob("*.json")):
        try:
            text = fp.read_text(encoding="utf-8").strip()
            if not text:
                continue
            if text.lstrip().startswith("["):
                # 配列 JSON
                arr = json.loads(text)
                if isinstance(arr, list):
                    out.extend(x for x in arr if isinstance(x, dict))
            else:
                # 行区切り JSON を想定
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict):
                            out.append(obj)
                    except Exception:
                        # 行単位のパース失敗はスキップ
                        continue
        except Exception:
            # 壊れたファイルはスキップ
            continue
    return out


try:
    # 任意依存。存在しない場合はフォールバックローダに切替
    from noctria_gui.services import statistics_service  # type: ignore

    def load_all_statistics() -> List[Dict[str, Any]]:
        try:
            logs = statistics_service.load_all_statistics()
            # dataclass 対応
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
# ユーティリティ
# ------------------------------------------------------------
def _to_pct_if_ratio(k: str, v: Any) -> Any:
    # win_rate / max_drawdown が 0..1 っぽければ % に変換
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


def _build_history_trend_dist(strategy_name: str, logs: List[Dict[str, Any]]):
    """履歴（hist）、日次トレンド（trend_dict）、分布（dist）を生成。"""
    hist = [log for log in logs if log.get("strategy") == strategy_name]
    if not hist:
        return None, None, None

    # 日次集計
    trend = defaultdict(lambda: defaultdict(list))  # date -> metric -> [values]
    dist = defaultdict(list)                        # metric -> [values]

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
            if arr:
                vals.append(round(sum(arr) / len(arr), m["dec"]))
            else:
                vals.append(None)
        avg, vmax, vmin = _agg(vals, m["dec"])
        diff = None
        if len([v for v in vals if v is not None]) >= 2:
            # 末尾の連続2点の差分（Noneは無視）
            tail = [v for v in vals if v is not None][-2:]
            diff = round(tail[-1] - tail[-2], m["dec"])
        trend_dict[k] = {
            "labels": dates,
            "values": vals,
            "avg": avg,
            "max": vmax,
            "min": vmin,
            "diff": diff,
        }
    return hist, trend_dict, dist


def _find_related_by_tags(all_logs: List[Dict[str, Any]],
                          strategy_name: str,
                          current_tags: List[str]) -> List[Dict[str, Any]]:
    if not current_tags:
        return []
    rel = []
    seen = set()
    for s in all_logs:
        name = s.get("strategy")
        if not name or name == strategy_name or name in seen:
            continue
        tags = s.get("tags") or []
        if any(t in (tags or []) for t in current_tags):
            rel.append(s)
            seen.add(name)
        if len(rel) >= 4:
            break
    return rel

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

    # データ読込（services が無ければフォールバック）
    try:
        logs = load_all_statistics()
    except Exception as e:
        logger.error("統計ログの読み込みに失敗: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="統計ログの読み込みに失敗しました。")

    # 戦略存在確認
    matched_strategy = next((log for log in logs if log.get("strategy") == strategy_name), None)
    if not matched_strategy:
        raise HTTPException(status_code=404, detail=f"戦略『{strategy_name}』は見つかりません。")

    # 関連戦略（タグ）
    current_tags = matched_strategy.get("tags") or []
    related_strategies = _find_related_by_tags(logs, strategy_name, current_tags)

    # 履歴/トレンド/分布
    hist, trend_dict, dist = _build_history_trend_dist(strategy_name, logs)
    if hist is None:
        raise HTTPException(status_code=404, detail="履歴情報が存在しません。")

    # raw=1 なら JSON 生返却
    base_payload = {
        "strategy": matched_strategy,
        "related_strategies": related_strategies,
        "dashboard_metrics": DASHBOARD_METRICS,
        "trend_dict": trend_dict,
        "metric_dist": dist,
        "eval_list": sorted(hist, key=lambda x: (x.get("evaluated_at") or ""), reverse=True),
        "trace_id": trace_id,
        "decision_id": decision_id,
    }
    if raw == 1:
        return JSONResponse(base_payload)

    # テンプレート選択（存在しなければ safe モードで簡易HTML）
    # 優先: templates/strategies/detail.html -> 従来: strategy_detail.html
    tpl_primary = NOCTRIA_GUI_TEMPLATES_DIR / "strategies" / "detail.html"
    tpl_legacy = NOCTRIA_GUI_TEMPLATES_DIR / "strategy_detail.html"
    context = {"request": request, **base_payload}

    if tpl_primary.exists():
        tpl_name = "strategies/detail.html"
    elif tpl_legacy.exists():
        tpl_name = "strategy_detail.html"
    else:
        tpl_name = None

    if tpl_name:
        if safe == 1:
            try:
                return templates.TemplateResponse(tpl_name, context)
            except Exception as e:
                logger.warning("テンプレ描画失敗。簡易HTMLにフォールバック: %s", e, exc_info=True)
                # fallthrough to simple HTML
        else:
            # safe=0 の場合はテンプレの例外をそのまま上げる
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

      <h2>KPIs / Trends (aggregated daily)</h2>
      <pre>{json.dumps(trend_dict, ensure_ascii=False, indent=2)}</pre>

      <h2>Distributions</h2>
      <pre>{json.dumps({k:list(map(float, v)) for k,v in (dist or {}).items()}, ensure_ascii=False, indent=2)}</pre>

      <h2>Evaluations</h2>
      <pre>{json.dumps(base_payload["eval_list"], ensure_ascii=False, indent=2)}</pre>

      {"<h2>Related</h2><pre>"+json.dumps(related_strategies, ensure_ascii=False, indent=2)+"</pre>" if related_strategies else ""}
    </body></html>
    """.strip()
    return HTMLResponse(content=simple, status_code=200)
