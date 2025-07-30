#!/usr/bin/env python3
# coding: utf-8

"""
🧠 Veritas Machina（理想形・統治AI経由専用）
- MLベースの戦略生成・評価・ランキングAI
- 戻り値にdecision_id, caller, ai_source等を付与
- 必ずNoctria王経由でのみ呼ばれる
"""

import subprocess
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import traceback

from src.core.path_config import (
    VERITAS_GENERATE_SCRIPT, VERITAS_EVAL_LOG, VERITAS_EVALUATE_SCRIPT, LOGS_DIR
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class VeritasMachina:
    def __init__(self):
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.error(f"ログディレクトリ作成失敗: {e}")
        self.generate_log_path = LOGS_DIR / "veritas_generate.log"
        self.evaluate_log_path = LOGS_DIR / "veritas_evaluate.log"

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
            logging.error(f"{desc}ログ保存時にエラー: {e}")

    def _build_cli_args(self, param_dict: Dict[str, Any]) -> List[str]:
        args = []
        try:
            for k, v in param_dict.items():
                args.append(f"--{k}")
                if isinstance(v, bool):
                    v = str(v).lower()
                args.append(str(v))
        except Exception as e:
            logging.error(f"CLI引数組立て失敗: {e}")
        return args

    def _make_explanation(self, best: dict, rankings: List[dict]) -> str:
        try:
            avg_win = sum(r.get("win_rate", 0) for r in rankings) / len(rankings) if rankings else 0
            avg_dd = sum(r.get("max_drawdown", 0) for r in rankings) / len(rankings) if rankings else 0
            best_wr = best.get("win_rate", None)
            best_dd = best.get("max_drawdown", None)
            best_sharpe = best.get("sharpe_ratio", None)
            lines = []
            if best_wr is not None:
                lines.append(f"勝率: {best_wr:.2f}%（合格戦略平均: {avg_win:.2f}%）")
            if best_dd is not None:
                lines.append(f"最大DD: {best_dd:.2f}（合格戦略平均: {avg_dd:.2f}）")
            if best_sharpe is not None:
                lines.append(f"シャープレシオ: {best_sharpe:.3f}")
            lines.append("final_capital最大かつ安定性・勝率等で最良だったため選定")
            return " / ".join(lines)
        except Exception as e:
            return f"自動説明生成エラー: {e}"

    def propose(
        self,
        top_n: int = 5,
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        **params
    ) -> Dict[str, Any]:
        try:
            # --- ML戦略生成 ---
            if not Path(VERITAS_GENERATE_SCRIPT).exists():
                msg = f"戦略生成スクリプトが見つかりません: {VERITAS_GENERATE_SCRIPT}"
                logging.error(msg)
                return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                        "type": "strategy_proposal", "status": "ERROR", "detail": msg, "strategy_rankings": [], "explanation": "", "params": params}
            try:
                logging.info(f"戦略生成プロセス開始（パラメータ: {params}）")
                cli_args = self._build_cli_args(params)
                res = subprocess.run(
                    ["python", str(VERITAS_GENERATE_SCRIPT)] + cli_args,
                    check=True, capture_output=True, text=True
                )
                self._save_subprocess_output(res, self.generate_log_path, "VERITAS GENERATE")
                logging.info("戦略生成プロセス完了。")
            except subprocess.CalledProcessError as e:
                self._save_subprocess_output(e, self.generate_log_path, "VERITAS GENERATE (FAILED)")
                error_message = f"戦略生成失敗: {e.stderr or e}"
                logging.error(error_message)
                return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                        "type": "strategy_proposal", "status": "ERROR", "detail": error_message, "strategy_rankings": [], "explanation": "", "params": params}
            except Exception as e:
                err_detail = traceback.format_exc()
                logging.error(f"戦略生成時エラー: {err_detail}")
                return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                        "type": "strategy_proposal", "status": "ERROR", "detail": f"戦略生成時エラー: {e}", "strategy_rankings": [], "explanation": "", "params": params}

            # --- ML評価 ---
            if not Path(VERITAS_EVALUATE_SCRIPT).exists():
                msg = f"戦略評価スクリプトが見つかりません: {VERITAS_EVALUATE_SCRIPT}"
                logging.error(msg)
                return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                        "type": "strategy_proposal", "status": "ERROR", "detail": msg, "strategy_rankings": [], "explanation": "", "params": params}
            try:
                logging.info("戦略評価プロセス開始。")
                cli_args = self._build_cli_args(params)
                res = subprocess.run(
                    ["python", str(VERITAS_EVALUATE_SCRIPT)] + cli_args,
                    check=True, capture_output=True, text=True
                )
                self._save_subprocess_output(res, self.evaluate_log_path, "VERITAS EVALUATE")
                logging.info("戦略評価プロセス完了。")
            except subprocess.CalledProcessError as e:
                self._save_subprocess_output(e, self.evaluate_log_path, "VERITAS EVALUATE (FAILED)")
                error_message = f"戦略評価失敗: {e.stderr or e}"
                logging.error(error_message)
                return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                        "type": "strategy_proposal", "status": "ERROR", "detail": error_message, "strategy_rankings": [], "explanation": "", "params": params}
            except Exception as e:
                err_detail = traceback.format_exc()
                logging.error(f"戦略評価時エラー: {err_detail}")
                return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                        "type": "strategy_proposal", "status": "ERROR", "detail": f"戦略評価時エラー: {e}", "strategy_rankings": [], "explanation": "", "params": params}

            # --- 戦略ランキング返却 ---
            if not Path(VERITAS_EVAL_LOG).exists():
                msg = f"評価ログ（{VERITAS_EVAL_LOG}）が見つかりません。"
                logging.error(msg)
                return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                        "type": "strategy_proposal", "status": "ERROR", "detail": msg, "strategy_rankings": [], "explanation": "", "params": params}
            try:
                logging.info("評価結果からランキング選定…")
                with open(VERITAS_EVAL_LOG, "r", encoding="utf-8") as f:
                    results = json.load(f)
                passed_strategies = [r for r in results if r.get("passed")]
                if not passed_strategies:
                    msg = "全ての戦略が評価基準を満たしませんでした。"
                    logging.warning(msg)
                    return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                            "type": "strategy_proposal", "status": "REJECTED", "detail": msg, "strategy_rankings": [], "explanation": "", "params": params}
                rankings: List[dict] = sorted(
                    passed_strategies,
                    key=lambda r: r.get("final_capital", 0),
                    reverse=True
                )[:top_n]
                best_strategy = rankings[0]
                explanation = self._make_explanation(best_strategy, rankings)
                logging.info(f"最良戦略『{best_strategy.get('strategy')}』選定: {explanation}")
                return {
                    "name": "VeritasMachina",
                    "ai_source": "veritas",
                    "decision_id": decision_id,
                    "caller": caller,
                    "type": "strategy_proposal",
                    "status": "PROPOSED",
                    "strategy_details": best_strategy,
                    "strategy_rankings": rankings,
                    "explanation": explanation,
                    "params": params
                }
            except (json.JSONDecodeError, KeyError) as e:
                msg = f"評価ログ破損 or 形式不正: {e}"
                logging.error(msg)
                return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                        "type": "strategy_proposal", "status": "ERROR", "detail": msg, "strategy_rankings": [], "explanation": "", "params": params}
            except Exception as e:
                err_detail = traceback.format_exc()
                logging.error(f"最良戦略抽出時エラー: {err_detail}")
                return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                        "type": "strategy_proposal", "status": "ERROR", "detail": f"最良戦略抽出時エラー: {e}", "strategy_rankings": [], "explanation": "", "params": params}

        except Exception as e:
            err_detail = traceback.format_exc()
            logging.error(f"致命的な例外: {err_detail}")
            return {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": decision_id, "caller": caller,
                    "type": "strategy_proposal", "status": "ERROR", "detail": f"致命的な例外: {e}", "strategy_rankings": [], "explanation": "", "params": params}

# ========================================
# ✅ テストブロック（王Noctria経由テスト例）
# ========================================
if __name__ == "__main__":
    try:
        logging.info("--- Veritas Machina: 理想形テスト開始 ---")
        strategist = VeritasMachina()
        proposal = strategist.propose(top_n=5, decision_id="KC-20250730-TEST", caller="king_noctria", risk=0.01, symbol="USDJPY", lookback=180)
        print("\n👑 王への進言（Veritas Machina）:")
        print(json.dumps(proposal, indent=4, ensure_ascii=False))
        logging.info("--- Veritas Machina: 理想形テスト完了 ---")
    except Exception as e:
        err_detail = traceback.format_exc()
        logging.error(f"メインブロックで致命的例外: {err_detail}")
        err_res = {"name": "VeritasMachina", "ai_source": "veritas", "decision_id": "TEST", "caller": "king_noctria",
                   "type": "strategy_proposal", "status": "ERROR", "detail": f"致命的な例外: {e}", "strategy_rankings": [], "explanation": "", "params": {}}
        print(json.dumps(err_res, indent=4, ensure_ascii=False))
