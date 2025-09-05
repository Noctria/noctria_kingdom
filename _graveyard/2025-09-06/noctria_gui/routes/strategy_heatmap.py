#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Strategy Heatmap Route (v2.0)
- 戦略ごとの統計（勝率、DDなど）を集計し、ヒートマップ表示やCSV出力を行う
"""

import logging
import json
import io
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

# --- 王国の基盤モジュールをインポート ---
# ✅ 修正: path_config.pyのリファクタリングに合わせて、正しい変数名をインポート
from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, ACT_LOG_DIR

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# ✅ 修正: ルーターのprefixを/statisticsに統一
router = APIRouter(prefix="/statistics", tags=["strategy-heatmap"])
# ✅ 修正: 正しい変数名を使用
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))


# --- 依存性注入（DI）によるデータ集計ロジックの共通化 ---
def get_strategy_stats(
    from_date_str: Optional[str] = Query(None, alias="from"),
    to_date_str: Optional[str] = Query(None, alias="to"),
    strategy_keyword: Optional[str] = Query(None, alias="strategy"),
) -> Dict[str, Dict[str, Any]]:
    """
    指定された条件で戦略ログを集計し、統計データを生成する共通関数。
    """
    logging.info(f"戦略統計の集計を開始します。キーワード: '{strategy_keyword}', 期間: {from_date_str} ~ {to_date_str}")
    
    from_date = datetime.strptime(from_date_str, "%Y-%m-%d") if from_date_str else None
    to_date = datetime.strptime(to_date_str, "%Y-%m-%d") if to_date_str else None

    stats = defaultdict(lambda: {"count": 0, "win_rates": [], "drawdowns": []})
    
    if not ACT_LOG_DIR.exists():
        logging.warning(f"戦略採用ログのディレクトリが見つかりません: {ACT_LOG_DIR}")
        return {}

    for file_path in ACT_LOG_DIR.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            date_str = data.get("promoted_at") or data.get("timestamp")
            if not date_str: continue
            
            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

            if from_date and date_obj.date() < from_date.date(): continue
            if to_date and date_obj.date() > to_date.date(): continue

            name = data.get("strategy", "").strip()
            if not name: continue
            if strategy_keyword and strategy_keyword.lower() not in name.lower(): continue

            score = data.get("score", {})
            win = score.get("win_rate")
            dd = score.get("max_drawdown")

            stats[name]["count"] += 1
            if isinstance(win, (int, float)): stats[name]["win_rates"].append(win)
            if isinstance(dd, (int, float)): stats[name]["drawdowns"].append(dd)

        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"ログファイルの処理中にエラーが発生しました: {file_path}, 詳細: {e}")
            continue

    final_stats = {}
    for name, values in stats.items():
        final_stats[name] = {
            "count": values["count"],
            "avg_win": round(sum(values["win_rates"]) / len(values["win_rates"]), 1) if values["win_rates"] else 0,
            "avg_dd": round(sum(values["drawdowns"]) / len(values["drawdowns"]), 1) if values["drawdowns"] else 0,
        }
    
    logging.info(f"{len(final_stats)}件の戦略について集計が完了しました。")
    return final_stats


# --- ルート定義 ---

@router.get("/strategy-heatmap", response_class=HTMLResponse)
async def strategy_heatmap(
    request: Request, 
    stats: Dict[str, Dict] = Depends(get_strategy_stats)
):
    """
    🧠 戦略別統計ヒートマップ（GUI表示）
    """
    # クエリパラメータをテンプレートに渡すためにリクエストから取得
    query_params = request.query_params
    return templates.TemplateResponse("strategy_heatmap.html", {
        "request": request,
        "data": stats,
        "filter": {
            "from": query_params.get("from", ""),
            "to": query_params.get("to", ""),
            "strategy": query_params.get("strategy", "")
        }
    })


@router.get("/strategy-heatmap/export", response_class=StreamingResponse)
async def export_strategy_heatmap_csv(
    stats: Dict[str, Dict] = Depends(get_strategy_stats)
):
    """
    📁 戦略別統計ヒートマップのCSV出力
    """
    if not stats:
        raise HTTPException(status_code=404, detail="エクスポート対象のデータがありません。")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["戦略名", "件数", "平均勝率（%）", "最大DD（%）"])
    for name, v in stats.items():
        writer.writerow([name, v["count"], v["avg_win"], v["avg_dd"]])

    output.seek(0)
    filename = f"strategy_heatmap_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
