import numpy as np
import tensorflow as tf
import shap
import lime
import lime.lime_tabular

class ExplainableAI:
    """
    Explainable AI: 予測の透明性を向上するために SHAP と LIME を統合

    Attributes:
        model (tf.keras.Model): 予測モデル
        shap_explainer: SHAP による説明器
        lime_explainer: LIME による説明器
    """
    def __init__(self, model, data_sample=None):
        """
        コンストラクタ

        Args:
            model (tf.keras.Model): 対象の予測モデル
            data_sample (np.array): SHAP と LIME の初期化用サンプルデータ
                                     (形状: (num_samples, num_features))。指定がない場合はダミーで作成。
        """
        self.model = model

        # 初期サンプルデータがなければ、モデルの入力形状に基づいてダミーデータを生成
        if data_sample is None:
            if hasattr(model, "input_shape"):
                num_features = model.input_shape[1]
            else:
                num_features = 10
            data_sample = np.zeros((50, num_features))
        
        # SHAPの初期化
        # モデルが深層学習の場合、DeepExplainer を利用する（場合により GradientExplainer も検討）
        self.shap_explainer = shap.DeepExplainer(model, data_sample)
        
        # LIMEの初期化（タブラー型データとして設定）
        self.lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=data_sample,
            feature_names=[f"feature_{i}" for i in range(data_sample.shape[1])],
            class_names=["output"],
            discretize_continuous=True
        )

    def explain_prediction_shap(self, market_data):
        """
        SHAP による予測説明: 指定した市場データに対する各特徴量の影響度（SHAP値）を返す

        Args:
            market_data (np.array): 説明対象のデータ (形状: (num_samples, num_features))
        
        Returns:
            list: 各出力層の SHAP 値のリスト（モデルによる）
        """
        shap_values = self.shap_explainer.shap_values(market_data)
        return shap_values

    def explain_prediction_lime(self, market_data):
        """
        LIME による予測説明: 単一の市場データサンプルに対する説明結果を取得

        Args:
            market_data (np.array): 説明対象のデータ（形状: (1, num_features)）
        
        Returns:
            explanation (LimeExplanation): LIME による説明オブジェクト
        """
        # LIME は 1サンプル単位での説明を想定しているので、flatten() で1次元に変換
        sample = market_data.flatten()
        # 予測関数として、モデルの predict メソッドを指定
        prediction_fn = lambda x: self.model.predict(x)
        explanation = self.lime_explainer.explain_instance(
            sample, 
            prediction_fn, 
            num_features=5
        )
        return explanation

    def visualize_shap(self, market_data):
        """
        SHAP 値の可視化: summary_plot を利用して全体の特徴量重要度を表示
        注意: 実行する環境によっては描画ウィンドウが表示される

        Args:
            market_data (np.array): 説明対象のデータ
        """
        shap_values = self.explain_prediction_shap(market_data)
        shap.summary_plot(shap_values, market_data)

# ✅ シンプルなテストシミュレーション
if __name__ == "__main__":
    # ダミーの Keras モデルを構築（入力次元: 10、出力: 1）
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(16, activation='relu', input_shape=(10,)),
        tf.keras.layers.Dense(1, activation='linear')
    ])
    model.compile(optimizer='adam', loss='mse')

    # ダミーのサンプルデータ（50サンプル、10特徴量）を用意
    sample_data = np.random.rand(50, 10)
    
    # Explainable AI モジュールを初期化
    explain_ai = ExplainableAI(model, data_sample=sample_data)
    
    # テスト用の市場データサンプル（形状: (1, 10)）
    test_market_data = np.random.rand(1, 10)
    prediction = model.predict(test_market_data)
    print("Prediction:", prediction)
    
    # SHAP による説明の取得
    shap_values = explain_ai.explain_prediction_shap(test_market_data)
    print("SHAP values:", shap_values)
    
    # LIME による説明の取得
    lime_explanation = explain_ai.explain_prediction_lime(test_market_data)
    print("LIME explanation:", lime_explanation.as_list())
    
    # ※ 可視化のサンプル（コード実行環境で実際にグラフを開く場合）
    # explain_ai.visualize_shap(test_market_data)
