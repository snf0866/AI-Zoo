"""
効用関数の管理を行うミックスイン
"""
import logging
import numpy as np
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class UtilityFunctionMixin:
    """効用関数に関連する機能を提供するミックスイン"""
    
    def initialize_utility_function(self):
        """効用関数のパラメータを初期化する"""
        # 評価の重み（デフォルト値）
        self.utility_alpha = np.array([1.0, 0.8, 0.6])
        # コストの重み（デフォルト値）
        self.utility_beta = np.array([0.5, 0.3, 0.2])
        # 評価の次元
        self.evaluation_dimensions = ['engagement', 'helpfulness', 'character_adherence']
        # コストの次元
        self.cost_dimensions = ['response_time', 'complexity', 'risk']
        
        logger.info(f"Utility function initialized with {len(self.evaluation_dimensions)} evaluation dimensions")
    
    def calculate_utility(self, 
                        evaluation_scores: np.ndarray, 
                        cost_scores: np.ndarray) -> float:
        """
        多次元評価スコアとコストに基づいて効用を計算する
        
        U = α·R - β·C
        
        Args:
            evaluation_scores: 複数次元の評価スコアを含む配列
            cost_scores: 複数次元のコストスコアを含む配列
            
        Returns:
            全体の効用スコア
        """
        if len(evaluation_scores) != len(self.utility_alpha):
            logger.warning(f"Evaluation dimensions mismatch: expected {len(self.utility_alpha)}, got {len(evaluation_scores)}")
            # 必要に応じて配列の長さを調整
            evaluation_scores = np.resize(evaluation_scores, len(self.utility_alpha))
            
        if len(cost_scores) != len(self.utility_beta):
            logger.warning(f"Cost dimensions mismatch: expected {len(self.utility_beta)}, got {len(cost_scores)}")
            # 必要に応じて配列の長さを調整
            cost_scores = np.resize(cost_scores, len(self.utility_beta))
            
        reward_term = np.dot(self.utility_alpha, evaluation_scores)
        cost_term = np.dot(self.utility_beta, cost_scores)
        
        utility = reward_term - cost_term
        logger.debug(f"Utility calculation: {reward_term} (reward) - {cost_term} (cost) = {utility}")
        
        return float(utility)
        
    def estimate_response_evaluation(self, response: str, context: Dict[str, Any]) -> np.ndarray:
        """
        予測される応答の評価スコアを推定する
        
        Args:
            response: 考慮中の応答テキスト
            context: 会話コンテキスト情報
            
        Returns:
            各評価次元のスコアを含むnumpy配列
        """
        scores = np.zeros(len(self.evaluation_dimensions))
        
        # エンゲージメントスコア（応答の長さ、質問の含有など）
        if 'engagement' in self.evaluation_dimensions:
            idx = self.evaluation_dimensions.index('engagement')
            # 応答の長さに基づくスコア（長すぎず短すぎない）
            length_score = min(len(response) / 500, 1.0) if len(response) < 500 else 2 - (len(response) / 500)
            # 質問を含むかどうか
            question_score = 0.2 if '?' in response else 0
            scores[idx] = min(0.7 * length_score + 0.3 * question_score, 1.0)
            
        # 役立ち度スコア
        if 'helpfulness' in self.evaluation_dimensions:
            idx = self.evaluation_dimensions.index('helpfulness')
            # 簡易推定 - 長さと構造化コンテンツ（箇条書き、番号付きリストなど）の存在
            structure_score = 0.3 if any(marker in response for marker in ['- ', '1. ', '* ']) else 0
            detail_score = min(len(response) / 800, 0.7)  # 詳細な回答は役立つ傾向がある
            scores[idx] = min(structure_score + detail_score, 1.0)
            
        # キャラクター忠実度スコア
        if 'character_adherence' in self.evaluation_dimensions:
            idx = self.evaluation_dimensions.index('character_adherence')
            # キャラクター設定から重要なキーワードやフレーズがあるか確認
            character_keywords = self._extract_character_keywords()
            keyword_matches = sum(1 for keyword in character_keywords if keyword.lower() in response.lower())
            keyword_score = min(keyword_matches / max(len(character_keywords), 1), 0.8)
            # 基本的にキャラクター忠実度は高いと仮定
            scores[idx] = min(0.7 + keyword_score, 1.0)
            
        return scores
        
    def estimate_response_cost(self, response: str, context: Dict[str, Any]) -> np.ndarray:
        """
        予測される応答のコストを推定する
        
        Args:
            response: 考慮中の応答テキスト
            context: 会話コンテキスト情報
            
        Returns:
            各コスト次元のスコアを含むnumpy配列
        """
        costs = np.zeros(len(self.cost_dimensions))
        
        # 応答時間コスト
        if 'response_time' in self.cost_dimensions:
            idx = self.cost_dimensions.index('response_time')
            # 長い応答は入力に時間がかかる
            chars_per_minute = 900  # 平均タイピング速度
            estimated_typing_time = len(response) / chars_per_minute  # 分単位
            costs[idx] = min(estimated_typing_time / 2, 1.0)  # 2分以上は最大コスト
            
        # 複雑さコスト
        if 'complexity' in self.cost_dimensions:
            idx = self.cost_dimensions.index('complexity')
            # 文の長さと複雑な単語に基づくコスト
            avg_sentence_length = len(response) / max(response.count('. ') + response.count('! ') + response.count('? '), 1)
            complexity_score = min(avg_sentence_length / 50, 0.8)  # 50文字以上の文はより複雑
            costs[idx] = complexity_score
            
        # リスクコスト
        if 'risk' in self.cost_dimensions:
            idx = self.cost_dimensions.index('risk')
            # 不適切または論争を呼ぶ内容を含むリスク（簡易実装）
            risky_topics = ['政治', '宗教', '賭博', '成人向け', 'politics', 'religion', 'gambling', 'adult']
            risk_score = sum(0.2 for topic in risky_topics if topic in response.lower())
            costs[idx] = min(risk_score, 1.0)
            
        return costs
        
    def select_optimal_response(self, response_candidates: List[str], context: Dict[str, Any]) -> str:
        """
        効用関数に基づいて最適な応答を選択する
        
        Args:
            response_candidates: 候補となる応答のリスト
            context: 会話コンテキスト情報
            
        Returns:
            最も高い効用スコアを持つ応答
        """
        best_utility = float('-inf')
        best_response = response_candidates[0] if response_candidates else ""
        
        for response in response_candidates:
            evaluation = self.estimate_response_evaluation(response, context)
            costs = self.estimate_response_cost(response, context)
            utility = self.calculate_utility(evaluation, costs)
            
            logger.debug(f"Response candidate utility: {utility}")
            logger.debug(f"- Evaluation scores: {evaluation}")
            logger.debug(f"- Cost scores: {costs}")
            
            if utility > best_utility:
                best_utility = utility
                best_response = response
                
        logger.info(f"Selected response with utility: {best_utility}")
        return best_response
        
    def update_utility_weights(self, alpha: np.ndarray = None, beta: np.ndarray = None):
        """
        効用関数の重みを更新する
        
        Args:
            alpha: 評価スコアの新しい重み
            beta: コストの新しい重み
        """
        if alpha is not None:
            if len(alpha) == len(self.utility_alpha):
                self.utility_alpha = alpha
                logger.info(f"Updated utility alpha weights: {alpha}")
            else:
                logger.warning(f"Alpha weights dimension mismatch: expected {len(self.utility_alpha)}, got {len(alpha)}")
                
        if beta is not None:
            if len(beta) == len(self.utility_beta):
                self.utility_beta = beta
                logger.info(f"Updated utility beta weights: {beta}")
            else:
                logger.warning(f"Beta weights dimension mismatch: expected {len(self.utility_beta)}, got {len(beta)}")