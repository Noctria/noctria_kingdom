"""
🧬 遺伝的アルゴリズム戦略の基本クラス
"""

import random
import numpy as np

class GeneticAlgorithm:
    def __init__(self, population_size=50, mutation_rate=0.01, generations=100):
        """
        ✅ 遺伝的アルゴリズムの初期化
        :param population_size: 集団のサイズ
        :param mutation_rate: 突然変異率
        :param generations: 進化回数
        """
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.generations = generations

    def _initialize_population(self, data_shape):
        """
        ✅ 初期集団をランダムに生成
        :param data_shape: 各個体のデータの形状
        """
        population = [np.random.rand(*data_shape) for _ in range(self.population_size)]
        return population

    def _evaluate_fitness(self, individual, market_data):
        """
        ✅ 各個体の適応度を評価（仮の評価関数例）
        :param individual: 個体の戦略パラメータ
        :param market_data: 市場データ
        """
        # 例: 市場データとの相関でスコア化
        score = np.dot(individual.flatten(), market_data.flatten())
        return score

    def _select_parents(self, population, fitnesses):
        """
        ✅ 適応度に基づき親を選択（ルーレット選択例）
        """
        total_fitness = sum(fitnesses)
        selection_probs = [f / total_fitness for f in fitnesses]
        parents = random.choices(population, weights=selection_probs, k=2)
        return parents

    def _crossover(self, parent1, parent2):
        """
        ✅ 親同士の交叉（1点交叉例）
        """
        point = random.randint(1, parent1.size - 1)
        child = np.concatenate((parent1.flatten()[:point], parent2.flatten()[point:]))
        return child.reshape(parent1.shape)

    def _mutate(self, individual):
        """
        ✅ 突然変異（ランダム要素の加算例）
        """
        if random.random() < self.mutation_rate:
            idx = random.randint(0, individual.size - 1)
            individual.flat[idx] += np.random.normal()
        return individual

    def optimize(self, market_data):
        """
        ✅ メイン進化ループ
        :param market_data: 市場データ
        """
        data_shape = market_data.shape
        population = self._initialize_population(data_shape)

        for _ in range(self.generations):
            fitnesses = [self._evaluate_fitness(ind, market_data) for ind in population]
            new_population = []
            for _ in range(self.population_size):
                p1, p2 = self._select_parents(population, fitnesses)
                child = self._crossover(p1, p2)
                child = self._mutate(child)
                new_population.append(child)
            population = new_population

        # 最終世代で最良個体を返す
        fitnesses = [self._evaluate_fitness(ind, market_data) for ind in population]
        best_idx = np.argmax(fitnesses)
        best_individual = population[best_idx]
        return best_individual
