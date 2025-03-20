# AI Zooボットの効用関数システム

## 概要

AIボットの応答生成プロセスにおいて、「どの応答が最適か」を判断することは重要な課題である。AI Zooボットでは、経済学や意思決定理論に由来する「効用関数（Utility Function）」の概念を導入し、複数の応答候補から最適な応答を選択する機能を実装している。

## 効用関数の思想的背景

効用関数とは、選択肢の価値や望ましさを数値化するための関数である。経済学では、合理的な意思決定者が最大の満足（効用）を得るために選択をすると考えられている。同様に、AIボットも各応答がもたらす「価値」と「コスト」のバランスを考慮して最適な応答を選択すべきである。

この考え方には以下の利点がある：

1. **多次元評価**: 応答の質を複数の観点から評価できる
2. **トレードオフの明示化**: 異なる目標間の優先順位を明確にできる
3. **一貫した意思決定**: 応答選択に一貫したロジックを適用できる
4. **カスタマイズ性**: ボットごとに異なる「個性」を表現するために重みを調整できる

## AI Zooの効用関数フレームワーク

AI Zooボットでは、効用関数を以下の数式で表現している：

```
U = α⋅R - β⋅C
```

ここで：
- **U**: 総合効用スコア
- **α**: 報酬（評価）の重みベクトル
- **R**: 評価スコアベクトル
- **β**: コストの重みベクトル
- **C**: コストスコアベクトル

この式は、「応答の望ましい特性がもたらす価値」から「応答に関連するコスト」を差し引いたものが総合的な効用であることを示している。

![効用関数の概念図](https://i.imgur.com/2kZ3yse.png)

## 実装構造

効用関数の実装は`mixins/utility_function.py`に`UtilityFunctionMixin`クラスとして実装されており、以下の主要コンポーネントで構成されている：

### 1. 効用関数の初期化と設定

```python
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
```

各ディメンションの意味：

#### 評価次元（Evaluation Dimensions）
- **engagement**: ユーザーの興味を引きやすさ
- **helpfulness**: 応答の役立ち度
- **character_adherence**: キャラクター設定への忠実度

#### コスト次元（Cost Dimensions）
- **response_time**: 応答生成にかかる時間
- **complexity**: 応答の複雑さ
- **risk**: 不適切または論争を呼ぶリスク

### 2. 効用計算の中核部分

```python
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
    reward_term = np.dot(self.utility_alpha, evaluation_scores)
    cost_term = np.dot(self.utility_beta, cost_scores)
    
    utility = reward_term - cost_term
    
    return float(utility)
```

効用計算は内積演算を使用して、各次元のスコアと重みを掛け合わせて合算している。

### 3. 評価スコアの推定機能

```python
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
    
    # エンゲージメントスコア
    if 'engagement' in self.evaluation_dimensions:
        idx = self.evaluation_dimensions.index('engagement')
        # 応答の長さと質問の有無に基づくスコア
        length_score = min(len(response) / 500, 1.0) if len(response) < 500 else 2 - (len(response) / 500)
        question_score = 0.2 if '?' in response else 0
        scores[idx] = min(0.7 * length_score + 0.3 * question_score, 1.0)
    
    # 役立ち度スコア
    if 'helpfulness' in self.evaluation_dimensions:
        idx = self.evaluation_dimensions.index('helpfulness')
        # 構造化コンテンツの存在と詳細さに基づくスコア
        structure_score = 0.3 if any(marker in response for marker in ['- ', '1. ', '* ']) else 0
        detail_score = min(len(response) / 800, 0.7)
        scores[idx] = min(structure_score + detail_score, 1.0)
    
    # キャラクター忠実度スコア
    if 'character_adherence' in self.evaluation_dimensions:
        idx = self.evaluation_dimensions.index('character_adherence')
        # キャラクター設定に関連するキーワードの存在に基づくスコア
        character_keywords = self._extract_character_keywords()
        keyword_matches = sum(1 for keyword in character_keywords if keyword.lower() in response.lower())
        keyword_score = min(keyword_matches / max(len(character_keywords), 1), 0.8)
        scores[idx] = min(0.7 + keyword_score, 1.0)
    
    return scores
```

### 4. コストスコアの推定機能

```python
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
        # 文の長さに基づくコスト
        avg_sentence_length = len(response) / max(response.count('. ') + response.count('! ') + response.count('? '), 1)
        costs[idx] = min(avg_sentence_length / 50, 0.8)
    
    # リスクコスト
    if 'risk' in self.cost_dimensions:
        idx = self.cost_dimensions.index('risk')
        # 不適切または論争を呼ぶトピックの存在に基づくコスト
        risky_topics = ['政治', '宗教', '賭博', '成人向け', 'politics', 'religion', 'gambling', 'adult']
        risk_score = sum(0.2 for topic in risky_topics if topic in response.lower())
        costs[idx] = min(risk_score, 1.0)
    
    return costs
```

### 5. 最適応答選択のメイン処理

```python
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
        
        if utility > best_utility:
            best_utility = utility
            best_response = response
    
    return best_response
```

## 効用関数の使用フロー

効用関数を使用した応答選択の流れは以下の通りである：

1. LLMサービスから複数の応答候補を生成（例：n=3）
2. 各応答候補に対して：
   - 評価スコアの推定（engagement, helpfulness, character_adherence）
   - コストスコアの推定（response_time, complexity, risk）
   - 効用スコアの計算 (U = α⋅R - β⋅C)
3. 最も高い効用スコアを持つ応答の選択
4. 選択された最適応答のユーザーへの送信

![応答選択フロー](https://i.imgur.com/LDj3Nt9.png)

## カスタマイズと拡張

効用関数システムは以下の方法でカスタマイズ可能である：

1. **重みの調整**: `utility_alpha`と`utility_beta`の値を変更して、どの要素を重視するかを調整する
2. **次元の追加**: 新たな評価次元やコスト次元を追加して、より多角的な評価を実現する
3. **推定ロジックの改善**: より洗練された方法でスコアを推定するようにアルゴリズムを改良する

```python
# 例：応答の長さを重視する設定
bot.update_utility_weights(
    alpha=np.array([1.5, 0.6, 0.4]),  # engagementの重みを1.5に上げる
    beta=np.array([0.3, 0.6, 0.2])    # complexityの重みを0.6に上げる
)
```

## 今後の展望

現在の効用関数システムは、シンプルなヒューリスティックに基づいているが、将来的には以下の拡張が考えられる：

1. **機械学習の導入**: ユーザーフィードバックに基づいてスコア推定モデルを学習する
2. **コンテキスト考慮の強化**: 会話履歴や相手の性格に基づいたスコア調整を行う
3. **感情分析の統合**: 応答の感情的トーンを考慮した効用計算を実装する
4. **リアルタイム調整**: 会話の流れに応じて効用関数の重みを動的に変更する

## まとめ

効用関数システムは、AIボットの応答選択プロセスに経済学的な意思決定モデルを適用することで、より賢明で状況に応じた応答を可能にする。単一のLLM出力に頼るのではなく、複数の候補から最適なものを選ぶことで、ボットの応答品質を向上させることができる。

また、このアプローチは、AIボットの意思決定プロセスを透明化し、特定の応答が選ばれた理由を説明可能にするという利点もある。これは、AIシステムの信頼性と説明可能性を高める重要な要素である。