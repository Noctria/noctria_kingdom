#!/usr/bin/env python3
# coding: utf-8
"""
👑 /api/king - 中央統治AI NoctriaのAPIルート（理想形・decision_id一元管理）
- 既存のコマンド系に加えて、Prometheus(学習→評価DAG)の
  ダッシュボード & 1クリック学習トリガを提供
"""

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path_config import NOCTRIA_GUI_TEMPLATES_DIR, LOGS_DIR
from src.core.king_noctria import KingNoctria

from datetime import datetime
from pathlib import Path
import os
import json
import logging
from typing import Dict, Any, Optional, Tuple

# 追加: Airflow REST API を叩くため
import requests
from requests.auth import HTTPBasicAuth

router = APIRouter(prefix="/api/king", tags=["King"])
templates = Jinja2Templates(directory=str(NOCTRIA_GUI_TEMPLATES_DIR))

KING_LOG_PATH = LOGS_DIR / "king_log.jsonl"  # 1行1レコード型を推奨
logger = logging.getLogger("king_routes")

# ====== Airflow REST API 設定（.env で上書き可） ======
AIRFLOW_BASE_URL = os.getenv("AIRFLOW_API_BASE", os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080"))
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
TRAIN_DAG_ID = "train_prometheus_obs8"

# ====== モデル格納ルート（.env で上書き可） ======
# path_config に DATA_DIR があるならそれを尊重。無い環境でも動くようにフォールバック。
try:
    from src.core.path_config import DATA_DIR as _DATA_DIR  # type: ignore
except Exception:
    _DATA_DIR = Path(os.getenv("NOCTRIA_DATA_DIR", Path.cwd() / "data"))

MODELS_DIR = Path(os.getenv("NOCTRIA_MODELS_ROOT", str(_DATA_DIR / "models")))
PROJECT = "prometheus"
ALGO = "PPO"
OBS_DIM = 8

# =========================================
# 既存機能
# =========================================

def load_logs() -> list[Dict[str, Any]]:
    try:
        if KING_LOG_PATH.exists():
            with open(KING_LOG_PATH, "r", encoding="utf-8") as f:
                return [json.loads(line) for line in f if line.strip()]
        return []
    except Exception as e:
        logger.error(f"🔴 load_logs失敗: {e}")
        return []

# KingNoctriaのインスタンスをグローバルに生成し共有
king_instance = KingNoctria()

@router.post("/command")
async def king_command_api(request: Request):
    """
    👑 王Noctriaによる統治コマンドAPI（全PDCA/DAG/AI指令を統一集約）
    """
    try:
        data = await request.json()
        command = data.get("command")
        if not command:
            raise HTTPException(status_code=400, detail="commandパラメータが必要です。")
        args = data.get("args", {})
        if not isinstance(args, dict):
            args = {}
        ai = data.get("ai", None)  # 将来対応用
        caller = "king_routes"
        reason = data.get("reason", f"APIコマンド[{command}]実行")

        if command == "council":
            result = king_instance.hold_council(args, caller=caller, reason=reason)
        elif command == "generate_strategy":
            result = king_instance.trigger_generate(args, caller=caller, reason=reason)
        elif command == "evaluate":
            result = king_instance.trigger_eval(args, caller=caller, reason=reason)
        elif command == "recheck":
            result = king_instance.trigger_recheck(args, caller=caller, reason=reason)
        elif command == "push":
            result = king_instance.trigger_push(args, caller=caller, reason=reason)
        elif command == "replay":
            log_path = args.get("log_path", "") if isinstance(args, dict) else ""
            result = king_instance.trigger_replay(log_path, caller=caller, reason=reason)
        else:
            return JSONResponse(content={"error": f"未知コマンド: {command}"}, status_code=400)

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"King command failed: {e}", exc_info=True)
        return JSONResponse(
            content={"error": f"King command failed: {str(e)}"},
            status_code=500
        )

@router.get("/history", response_class=HTMLResponse)
async def show_king_history(request: Request):
    """
    📜 KingNoctriaによる過去の評議会（全統治コマンド）履歴GUI
    """
    try:
        logs = load_logs()
        logs = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)
        return templates.TemplateResponse("king_history.html", {
            "request": request,
            "logs": logs
        })
    except Exception as e:
        logger.error(f"ログ読み込みエラー: {e}", exc_info=True)
        return templates.TemplateResponse("king_history.html", {
            "request": request,
            "logs": [],
            "error": f"ログ読み込みエラー: {str(e)}"
        })

# =========================================
# 追加: Prometheus ダッシュボード & 1クリック学習
# =========================================

def _resolve_latest_dir(base: Path) -> Optional[Path]:
    """
    base/obs8/ 配下の最新ディレクトリを返す。latest シンボリックリンクがあればそれを優先。
    """
    obs_dir = base / PROJECT / ALGO / f"obs{OBS_DIM}"
    if not obs_dir.exists():
        return None

    latest = obs_dir / "latest"
    try:
        if latest.exists():
            # シンボリックリンクの実体を解決
            return Path(os.path.realpath(str(latest)))
    except Exception:
        pass

    # latest が無い場合は mtime の新しいディレクトリを選ぶ
    candidates = [p for p in obs_dir.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]

def _load_latest_model_info() -> Tuple[Optional[Path], Dict[str, Any]]:
    """
    最新モデルディレクトリと metadata.json を返す（無ければ空）
    """
    latest_dir = _resolve_latest_dir(MODELS_DIR)
    if not latest_dir:
        return None, {}

    meta_path = latest_dir / "metadata.json"
    meta: Dict[str, Any] = {}
    try:
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"metadata.json 読み込み失敗: {e}")
    return latest_dir, meta

def _airflow_trigger_train(conf: Dict[str, Any]) -> Dict[str, Any]:
    """
    Airflow REST API: POST /api/v1/dags/{dag_id}/dagRuns
    """
    url = f"{AIRFLOW_BASE_URL}/api/v1/dags/{TRAIN_DAG_ID}/dagRuns"
    payload = {"conf": conf}
    try:
        r = requests.post(
            url,
            json=payload,
            auth=HTTPBasicAuth(AIRFLOW_USER, AIRFLOW_PASSWORD),
            timeout=15,
        )
        if r.status_code >= 300:
            raise RuntimeError(f"Airflow API error {r.status_code}: {r.text}")
        return r.json()
    except Exception as e:
        logger.error(f"Airflow trigger failed: {e}")
        raise

def _to_bool(v: Any, default: bool = True) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "y", "on")
    return default

def _maybe_cast(v: str, caster, default=None):
    if v is None or v == "":
        return default
    try:
        return caster(v)
    except Exception:
        return default

@router.get("/prometheus", response_class=HTMLResponse)
async def king_prometheus_dashboard(request: Request):
    """
    👑 Prometheus 学習ダッシュボード
    - 最新モデルのメタ＆評価結果の表示
    - 学習＆評価の1クリックトリガフォーム
    """
    latest_dir, meta = _load_latest_model_info()
    return templates.TemplateResponse(
        "king_prometheus.html",
        {
            "request": request,
            "latest_dir": str(latest_dir) if latest_dir else None,
            "meta": meta,
            "message": None,
            "error": None,
            "airflow_base": AIRFLOW_BASE_URL,
            "train_dag_id": TRAIN_DAG_ID,
        },
    )

@router.post("/prometheus/train", response_class=HTMLResponse)
async def king_prometheus_train(
    request: Request,
    # --- フォームの各フィールド（未入力はNoneで受け取り、サーバ側で省略） ---
    TOTAL_TIMESTEPS: Optional[str] = Form(default=None),
    learning_rate: Optional[str] = Form(default=None),
    n_steps: Optional[str] = Form(default=None),
    batch_size: Optional[str] = Form(default=None),
    n_epochs: Optional[str] = Form(default=None),
    gamma: Optional[str] = Form(default=None),
    gae_lambda: Optional[str] = Form(default=None),
    ent_coef: Optional[str] = Form(default=None),
    vf_coef: Optional[str] = Form(default=None),
    max_grad_norm: Optional[str] = Form(default=None),
    clip_range: Optional[str] = Form(default=None),
    clip_range_vf: Optional[str] = Form(default=None),
    seed: Optional[str] = Form(default=None),
    eval_n_episodes: Optional[str] = Form(default=None),
    eval_deterministic: Optional[str] = Form(default="true"),
):
    """
    フォーム値を --conf に変換して Airflow の train_prometheus_obs8 をトリガ
    """
    conf: Dict[str, Any] = {}
    # 数値系は安全にキャスト（未入力は省略）
    if (v := _maybe_cast(TOTAL_TIMESTEPS, int)) is not None: conf["TOTAL_TIMESTEPS"] = v
    if (v := _maybe_cast(learning_rate, float)) is not None: conf["learning_rate"] = v
    if (v := _maybe_cast(n_steps, int)) is not None: conf["n_steps"] = v
    if (v := _maybe_cast(batch_size, int)) is not None: conf["batch_size"] = v
    if (v := _maybe_cast(n_epochs, int)) is not None: conf["n_epochs"] = v
    if (v := _maybe_cast(gamma, float)) is not None: conf["gamma"] = v
    if (v := _maybe_cast(gae_lambda, float)) is not None: conf["gae_lambda"] = v
    if (v := _maybe_cast(ent_coef, float)) is not None: conf["ent_coef"] = v
    if (v := _maybe_cast(vf_coef, float)) is not None: conf["vf_coef"] = v
    if (v := _maybe_cast(max_grad_norm, float)) is not None: conf["max_grad_norm"] = v
    if (v := _maybe_cast(clip_range, float)) is not None: conf["clip_range"] = v
    if (v := _maybe_cast(clip_range_vf, float)) is not None: conf["clip_range_vf"] = v
    if (v := _maybe_cast(seed, int)) is not None: conf["seed"] = v
    if (v := _maybe_cast(eval_n_episodes, int)) is not None: conf["eval_n_episodes"] = v
    conf["eval_deterministic"] = _to_bool(eval_deterministic, True)

    message, error = None, None
    try:
        api_res = _airflow_trigger_train(conf)
        # Airflow 2.x は dag_run_id などを返す
        dag_run_id = api_res.get("dag_run_id", "(unknown)")
        message = f"🚀 Triggered DAG: {TRAIN_DAG_ID} (run_id={dag_run_id})"
    except Exception as e:
        error = f"Airflow trigger failed: {e}"

    latest_dir, meta = _load_latest_model_info()
    return templates.TemplateResponse(
        "king_prometheus.html",
        {
            "request": request,
            "latest_dir": str(latest_dir) if latest_dir else None,
            "meta": meta,
            "message": message,
            "error": error,
            "airflow_base": AIRFLOW_BASE_URL,
            "train_dag_id": TRAIN_DAG_ID,
        },
    )
