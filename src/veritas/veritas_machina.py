# src/veritas/veritas_machina.py
#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas Machina（MLベースの戦略生成・評価・ランキング）
- MLスクリプトで戦略を「生成→評価」し、ランキングを返す
- 返却に decision_id / caller / ai_source / trace_id を含める
- 生成・評価のサブプロセス出力をログファイルへ保存
- すべての結果（成功/警告/失敗）を agent_logs（SQLite）へ保存（全エージェント共通の運用）
- LLMは使わない（ML中心）。共通SPの統治方針は実装・返却ポリシーで遵守
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.path_config import (
    LOGS_DIR,
    VERITAS_EVAL_LOG,
    VERITAS_EVALUATE_SCRIPT,
    VERITAS_GENERATE_SCRIPT,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
LOG = logging.getLogger("VeritasMachina")


# =============================================================================
# DB（agent_logs）— run_pdca_agents.py のテーブル互換
# =============================================================================
def _db_path() -> Path:
    # 既定: src/codex_reports/pdca_log.db
    root = Path(__file__).resolve().parents[2]
    return Path(os.getenv("NOCTRIA_PDCA_DB", str(root / "src" / "codex_reports" / "pdca_log.db")))


def _db_connect() -> Optional[sqlite3.Connection]:
    try:
        dbp = _db_path()
        dbp.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(dbp)
        # 必要なら最小スキーマを作成（存在すれば no-op）
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT,
                role TEXT,
                title TEXT,
                content TEXT,
                created_at TEXT
            );
            """
        )
        return conn
    except Exception as e:
        LOG.warning("agent_logs DB接続に失敗: %s", e)
        return None


def _db_log_agent(role: str, title: str, content: str, trace_id: Optional[str]) -> None:
    conn = _db_connect()
    if not conn:
        return
    try:
        jst = timezone(timedelta(hours=9))
        ts = datetime.now(tz=jst).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO agent_logs (trace_id, role, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (trace_id or "", role, title, content, ts),
        )
        conn.commit()
    except Exception as e:
        LOG.warning("agent_logs への書き込みに失敗: %s", e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =============================================================================
# 本体
# =============================================================================
class VeritasMachina:
    def __init__(self):
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            LOG.error("ログディレクトリ作成失敗: %s", e)
        self.generate_log_path = LOGS_DIR / "veritas_generate.log"
        self.evaluate_log_path = LOGS_DIR / "veritas_evaluate.log"

    # --- 共通: サブプロセス出力をファイルへ保存 ---
    def _save_subprocess_output(self, proc: Any, log_path: Path, desc: str = ""):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- {desc} [{datetime.now()}] ---\n")
                f.write("STDOUT:\n")
                out = getattr(proc, "stdout", "") or ""
                err = getattr(proc, "stderr", "") or ""
                if isinstance(out, bytes):
                    out = out.decode("utf-8", errors="ignore")
                if isinstance(err, bytes):
                    err = err.decode("utf-8", errors="ignore")
                f.write(out)
                f.write("\nSTDERR:\n")
                f.write(err)
                f.write("\n")
        except Exception as e:
            LOG.error("%s ログ保存時にエラー: %s", desc, e)

    # --- 共通: パラメータ辞書 → CLI引数 ---
    def _build_cli_args(self, param_dict: Dict[str, Any]) -> List[str]:
        args: List[str] = []
        try:
            for k, v in (param_dict or {}).items():
                args.append(f"--{k}")
                if isinstance(v, bool):
                    v = str(v).lower()
                args.append(str(v))
        except Exception as e:
            LOG.error("CLI引数組立て失敗: %s", e)
        return args

    # --- 共通: 説明文（軽量ヒューリスティック） ---
    def _make_explanation(self, best: dict, rankings: List[dict]) -> str:
        try:
            avg_win = sum(r.get("win_rate", 0) for r in rankings) / len(rankings) if rankings else 0
            avg_dd = (
                sum(r.get("max_drawdown", 0) for r in rankings) / len(rankings) if rankings else 0
            )
            best_wr = best.get("win_rate")
            best_dd = best.get("max_drawdown")
            best_sharpe = best.get("sharpe_ratio")
            lines: List[str] = []
            if isinstance(best_wr, (int, float)):
                lines.append(f"勝率: {best_wr:.2f}%（合格平均: {avg_win:.2f}%）")
            if isinstance(best_dd, (int, float)):
                lines.append(f"最大DD: {best_dd:.2f}（合格平均: {avg_dd:.2f}）")
            if isinstance(best_sharpe, (int, float)):
                lines.append(f"シャープ: {best_sharpe:.3f}")
            lines.append("final_capital と安定性指標の総合で最良と判断")
            return " / ".join(lines)
        except Exception as e:
            return f"自動説明生成エラー: {e}"

    # --- 共通: 最終結果をログして返す ---
    def _finalize(self, result: Dict[str, Any], trace_id: Optional[str]) -> Dict[str, Any]:
        # trace_id を明示反映してから agent_logs へ保存
        if trace_id:
            result.setdefault("trace_id", trace_id)
        try:
            _db_log_agent(
                role="veritas",
                title=f"Veritas {result.get('status', 'RESULT')}",
                content=json.dumps(result, ensure_ascii=False),
                trace_id=trace_id,
            )
        except Exception:
            pass
        return result

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def propose(
        self,
        top_n: int = 5,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        trace_id: Optional[str] = None,
        **params,
    ) -> Dict[str, Any]:
        """
        MLベースの戦略を生成→評価し、上位候補を返す。
        - すべてのフェーズで例外時もエラー結果を返し agent_logs に記録
        - params はそのまま生成/評価スクリプトへ --key value でパス
        """
        try:
            # --- 生成スクリプト存在チェック ---
            if not Path(VERITAS_GENERATE_SCRIPT).exists():
                msg = f"戦略生成スクリプトが見つかりません: {VERITAS_GENERATE_SCRIPT}"
                LOG.error(msg)
                return self._finalize(
                    {
                        "name": "VeritasMachina",
                        "ai_source": "veritas",
                        "decision_id": decision_id,
                        "caller": caller,
                        "type": "strategy_proposal",
                        "status": "ERROR",
                        "detail": msg,
                        "strategy_rankings": [],
                        "explanation": "",
                        "params": params,
                    },
                    trace_id,
                )

            # --- 戦略生成 ---
            try:
                LOG.info("戦略生成プロセス開始（params=%s）", params)
                cli_args = self._build_cli_args(params)
                res = subprocess.run(
                    ["python", str(VERITAS_GENERATE_SCRIPT)] + cli_args,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self._save_subprocess_output(res, self.generate_log_path, "VERITAS GENERATE")
                LOG.info("戦略生成プロセス完了")
            except subprocess.CalledProcessError as e:
                self._save_subprocess_output(e, self.generate_log_path, "VERITAS GENERATE (FAILED)")
                error_message = f"戦略生成失敗: {e.stderr or e}"
                LOG.error(error_message)
                return self._finalize(
                    {
                        "name": "VeritasMachina",
                        "ai_source": "veritas",
                        "decision_id": decision_id,
                        "caller": caller,
                        "type": "strategy_proposal",
                        "status": "ERROR",
                        "detail": error_message,
                        "strategy_rankings": [],
                        "explanation": "",
                        "params": params,
                    },
                    trace_id,
                )
            except Exception as e:
                LOG.error("戦略生成時エラー: %s", traceback.format_exc())
                return self._finalize(
                    {
                        "name": "VeritasMachina",
                        "ai_source": "veritas",
                        "decision_id": decision_id,
                        "caller": caller,
                        "type": "strategy_proposal",
                        "status": "ERROR",
                        "detail": f"戦略生成時エラー: {e}",
                        "strategy_rankings": [],
                        "explanation": "",
                        "params": params,
                    },
                    trace_id,
                )

            # --- 評価スクリプト存在チェック ---
            if not Path(VERITAS_EVALUATE_SCRIPT).exists():
                msg = f"戦略評価スクリプトが見つかりません: {VERITAS_EVALUATE_SCRIPT}"
                LOG.error(msg)
                return self._finalize(
                    {
                        "name": "VeritasMachina",
                        "ai_source": "veritas",
                        "decision_id": decision_id,
                        "caller": caller,
                        "type": "strategy_proposal",
                        "status": "ERROR",
                        "detail": msg,
                        "strategy_rankings": [],
                        "explanation": "",
                        "params": params,
                    },
                    trace_id,
                )

            # --- 戦略評価 ---
            try:
                LOG.info("戦略評価プロセス開始")
                cli_args = self._build_cli_args(params)
                res = subprocess.run(
                    ["python", str(VERITAS_EVALUATE_SCRIPT)] + cli_args,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self._save_subprocess_output(res, self.evaluate_log_path, "VERITAS EVALUATE")
                LOG.info("戦略評価プロセス完了")
            except subprocess.CalledProcessError as e:
                self._save_subprocess_output(e, self.evaluate_log_path, "VERITAS EVALUATE (FAILED)")
                error_message = f"戦略評価失敗: {e.stderr or e}"
                LOG.error(error_message)
                return self._finalize(
                    {
                        "name": "VeritasMachina",
                        "ai_source": "veritas",
                        "decision_id": decision_id,
                        "caller": caller,
                        "type": "strategy_proposal",
                        "status": "ERROR",
                        "detail": error_message,
                        "strategy_rankings": [],
                        "explanation": "",
                        "params": params,
                    },
                    trace_id,
                )
            except Exception as e:
                LOG.error("戦略評価時エラー: %s", traceback.format_exc())
                return self._finalize(
                    {
                        "name": "VeritasMachina",
                        "ai_source": "veritas",
                        "decision_id": decision_id,
                        "caller": caller,
                        "type": "strategy_proposal",
                        "status": "ERROR",
                        "detail": f"戦略評価時エラー: {e}",
                        "strategy_rankings": [],
                        "explanation": "",
                        "params": params,
                    },
                    trace_id,
                )

            # --- 評価ログからランキング抽出 ---
            if not Path(VERITAS_EVAL_LOG).exists():
                msg = f"評価ログが見つかりません: {VERITAS_EVAL_LOG}"
                LOG.error(msg)
                return self._finalize(
                    {
                        "name": "VeritasMachina",
                        "ai_source": "veritas",
                        "decision_id": decision_id,
                        "caller": caller,
                        "type": "strategy_proposal",
                        "status": "ERROR",
                        "detail": msg,
                        "strategy_rankings": [],
                        "explanation": "",
                        "params": params,
                    },
                    trace_id,
                )

            try:
                LOG.info("評価結果からランキング選定…")
                with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
                    results = json.load(f)

                passed = [r for r in results if r.get("passed")]
                if not passed:
                    msg = "全ての戦略が評価基準を満たしませんでした。"
                    LOG.warning(msg)
                    return self._finalize(
                        {
                            "name": "VeritasMachina",
                            "ai_source": "veritas",
                            "decision_id": decision_id,
                            "caller": caller,
                            "type": "strategy_proposal",
                            "status": "REJECTED",
                            "detail": msg,
                            "strategy_rankings": [],
                            "explanation": "",
                            "params": params,
                        },
                        trace_id,
                    )

                rankings: List[dict] = sorted(
                    passed, key=lambda r: r.get("final_capital", 0), reverse=True
                )[: top_n if isinstance(top_n, int) and top_n > 0 else 5]

                best = rankings[0]
                explanation = self._make_explanation(best, rankings)
                LOG.info("最良戦略『%s』選定: %s", best.get("strategy"), explanation)

                return self._finalize(
                    {
                        "name": "VeritasMachina",
                        "ai_source": "veritas",
                        "decision_id": decision_id,
                        "caller": caller,
                        "type": "strategy_proposal",
                        "status": "PROPOSED",
                        "strategy_details": best,
                        "strategy_rankings": rankings,
                        "explanation": explanation,
                        "params": params,
                    },
                    trace_id,
                )

            except (json.JSONDecodeError, KeyError) as e:
                msg = f"評価ログ破損/形式不正: {e}"
                LOG.error(msg)
                return self._finalize(
                    {
                        "name": "VeritasMachina",
                        "ai_source": "veritas",
                        "decision_id": decision_id,
                        "caller": caller,
                        "type": "strategy_proposal",
                        "status": "ERROR",
                        "detail": msg,
                        "strategy_rankings": [],
                        "explanation": "",
                        "params": params,
                    },
                    trace_id,
                )
            except Exception as e:
                LOG.error("最良戦略抽出時エラー: %s", traceback.format_exc())
                return self._finalize(
                    {
                        "name": "VeritasMachina",
                        "ai_source": "veritas",
                        "decision_id": decision_id,
                        "caller": caller,
                        "type": "strategy_proposal",
                        "status": "ERROR",
                        "detail": f"最良戦略抽出時エラー: {e}",
                        "strategy_rankings": [],
                        "explanation": "",
                        "params": params,
                    },
                    trace_id,
                )

        except Exception as e:
            LOG.error("致命的な例外: %s", traceback.format_exc())
            return self._finalize(
                {
                    "name": "VeritasMachina",
                    "ai_source": "veritas",
                    "decision_id": decision_id,
                    "caller": caller,
                    "type": "strategy_proposal",
                    "status": "ERROR",
                    "detail": f"致命的な例外: {e}",
                    "strategy_rankings": [],
                    "explanation": "",
                    "params": params,
                },
                trace_id,
            )


# ========================================
# ✅ 単体テスト（直接起動時）
# ========================================
if __name__ == "__main__":
    try:
        LOG.info("--- Veritas Machina: self-test ---")
        strategist = VeritasMachina()
        proposal = strategist.propose(
            top_n=5,
            decision_id="KC-TEST",
            caller="king_noctria",
            trace_id="trace_test_001",
            risk=0.01,
            symbol="USDJPY",
            lookback=180,
        )
        print("\n👑 王への進言（Veritas Machina）:")
        print(json.dumps(proposal, indent=4, ensure_ascii=False))
        LOG.info("--- Veritas Machina: self-test done ---")
    except Exception:
        LOG.error("メインブロック例外: %s", traceback.format_exc())
