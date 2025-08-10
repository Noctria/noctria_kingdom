# src/core/risk_manager.py
import logging
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.tsa.holtwinters import ExponentialSmoothing

logger = logging.getLogger(__name__)


class RiskManager:
    """Noctria Kingdom のリスク管理モジュール（Close 欄の自動補完に対応）"""

    def __init__(self, historical_data: Optional[pd.DataFrame] = None, price_col: Optional[str] = None):
        """
        初期化：リスク評価に使用する市場データをロード
        :param historical_data: pd.DataFrame | None
            価格データ（'Close'列が理想だが、無ければ自動補完を試みる）
        :param price_col: Optional[str]
            'Close' 欄に使う明示列名（あれば最優先採用）
        """
        self.data: Optional[pd.DataFrame] = None
        self.volatility: float = 0.0
        self.value_at_risk: float = np.inf

        if historical_data is None or len(historical_data) == 0:
            logger.warning("【RiskManager初期化】履歴データが空です。リスク機能を限定モードにします。")
            return

        # コピーして作業
        self.data = historical_data.copy()

        # 'Close' 欄の確保（price_col > 推測 > Bid/Ask ミッド > Open 代用）
        self._ensure_close_column(price_col=price_col)

        if "Close" not in self.data.columns:
            logger.warning("【RiskManager初期化】'Close' 欄を補えませんでした。リスク機能を限定モードにします。")
            self.data = None
            return

        # 指標の事前計算
        self.volatility = self.calculate_volatility()
        self.value_at_risk = self.calculate_var()

    # ------------------------------------------------------------------
    # 内部ユーティリティ
    # ------------------------------------------------------------------
    def _ensure_close_column(self, price_col: Optional[str] = None) -> None:
        """
        self.data に 'Close' 欄が無い場合に、以下の順で補う:
        1) price_col 明示指定
        2) 大文字小文字ゆらぎ 'close'
        3) よくある別名（closeprice/adj close/adjclose/price/last）
        4) Bid/Ask の平均でミッドプライス
        5) Open を暫定 Close に（最終手段）
        """
        if self.data is None or self.data.empty:
            return

        cols_lower = {c.lower(): c for c in self.data.columns}

        # 1) 明示指定
        if price_col and price_col in self.data.columns:
            self.data["Close"] = self.data[price_col]
            logger.info("RiskManager: 明示列 '%s' を Close として使用します。", price_col)
            return

        # 2) 大文字小文字ゆらぎ
        if "close" in cols_lower:
            self.data["Close"] = self.data[cols_lower["close"]]
            return

        # 3) よくある別名
        for alias in ("closeprice", "adj close", "adjclose", "price", "last"):
            if alias in cols_lower:
                self.data["Close"] = self.data[cols_lower[alias]]
                logger.info("RiskManager: 列 '%s' を Close として使用します。", cols_lower[alias])
                return

        # 4) Bid/Ask からミッド合成
        if "bid" in cols_lower and "ask" in cols_lower:
            b, a = cols_lower["bid"], cols_lower["ask"]
            self.data["Close"] = (self.data[b] + self.data[a]) / 2.0
            logger.info("RiskManager: Bid/Ask から Close(mid) を合成しました。")
            return

        # 5) Open を暫定 Close に
        if "open" in cols_lower:
            self.data["Close"] = self.data[cols_lower["open"]]
            logger.warning("RiskManager: Close 不在のため Open を暫定 Close として使用します。")
            return

        # ここまで来たら補えない
        # 呼び出し元で 'Close' 不在を検知して限定モードに落とす

    # ------------------------------------------------------------------
    # 指標計算
    # ------------------------------------------------------------------
    def calculate_volatility(self) -> float:
        """市場ボラティリティ（対数リターンの標準偏差）を算出"""
        if self.data is None or self.data.empty or "Close" not in self.data.columns:
            logger.warning("【RiskManager】ボラティリティ算出時にデータが欠損しています。")
            return 0.0
        closes = self.data["Close"].astype(float)
        returns = np.log(closes / closes.shift(1)).dropna()
        if returns.empty:
            logger.warning("【RiskManager】ボラティリティ算出時、リターン系列が空です。")
            return 0.0
        return float(returns.std())

    def calculate_var(self, confidence_level: float = 0.95) -> float:
        """
        VaR (Value at Risk) を正規分布前提で計算（損失側を正の値で返す）
        VaR = -(mean + z * std) を 0 以上で返す
        """
        if self.data is None or self.data.empty or "Close" not in self.data.columns:
            logger.warning("【RiskManager】VaR算出時に必要なデータが不足しています。")
            return np.inf
        closes = self.data["Close"].astype(float)
        pct_changes = closes.pct_change().dropna()
        if pct_changes.empty:
            logger.warning("【RiskManager】VaR算出時、リターン系列が空です。")
            return np.inf
        mean_return = float(np.mean(pct_changes))
        std_dev = float(np.std(pct_changes))
        z_score = float(norm.ppf(confidence_level))
        var = -(mean_return + z_score * std_dev)
        return max(var, 0.0)

    def calculate_var_ratio(self, price: float, confidence_level: float = 0.95) -> float:
        """VaR を現価格比で返す（Noctus 等で利用）"""
        var = self.calculate_var(confidence_level)
        if price == 0 or np.isinf(var):
            return 1.0
        return float(var / price)

    def adjust_stop_loss(self, current_price: float) -> float:
        """市場ボラティリティに応じてストップロス値を調整"""
        if self.volatility <= 0:
            return float(current_price * 0.95)
        stop_loss_level = current_price - (self.volatility * 2.0)
        return float(max(stop_loss_level, current_price * 0.95))

    def detect_anomalies(self):
        """
        異常検知 (Holt-Winters 平滑法, 例外ラップ付)
        戻り値: (異常あり: bool, 異常インデックス: list)
        """
        if (
            self.data is None
            or len(self.data) < 20
            or "Close" not in self.data.columns
            or self.volatility <= 0
        ):
            logger.warning("【RiskManager】異常検知に必要なデータ/指標が不足しています。")
            return False, []

        try:
            model = ExponentialSmoothing(self.data["Close"], trend="add", seasonal=None)
            fitted_model = model.fit()
            residuals = self.data["Close"] - fitted_model.fittedvalues
            anomalies = self.data[residuals.abs() > (2 * self.volatility)]
            is_anomaly = len(anomalies) > 0
            return is_anomaly, anomalies.index.tolist()
        except Exception as e:
            logger.error(f"【RiskManager】異常検知モデル構築/予測エラー: {e}")
            return False, []

    def optimal_position_size(self, capital: float, risk_per_trade: float = 0.02) -> float:
        """ポジションサイズ最適化（資本とリスク許容度）"""
        if self.value_at_risk is None or self.value_at_risk <= 0 or np.isinf(self.value_at_risk):
            logger.warning("【RiskManager】ポジションサイズ計算時、VaR値が無効です。")
            return 0.0
        return float(capital * risk_per_trade / self.value_at_risk)


# ✅ 単体テスト（直接実行時のみ）
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

    # Close ありのケース
    sample_data = pd.DataFrame({"Close": np.random.normal(loc=100, scale=5, size=100)})
    rm = RiskManager(sample_data)
    print("📊 市場ボラ:", rm.volatility)
    print("📉 VaR:", rm.value_at_risk)
    print("📉 VaR比率:", rm.calculate_var_ratio(102))
    print("🛡️ SL:", rm.adjust_stop_loss(102))
    print("🚨 異常:", rm.detect_anomalies())

    # Close なし（Bid/Ask から補完）
    sample_ba = pd.DataFrame({
        "Bid": np.random.normal(100, 0.5, 120),
        "Ask": np.random.normal(100.1, 0.5, 120),
    })
    rm2 = RiskManager(sample_ba)
    print("📊(BA) 市場ボラ:", rm2.volatility, "Close 有無:", "Close" in (rm2.data.columns if rm2.data is not None else []))

    # 別名から補完
    sample_alias = pd.DataFrame({"Price": np.random.normal(100, 1.0, 80)})
    rm3 = RiskManager(sample_alias)
    print("📊(alias) 市場ボラ:", rm3.volatility, "Close 有無:", "Close" in (rm3.data.columns if rm3.data is not None else []))
