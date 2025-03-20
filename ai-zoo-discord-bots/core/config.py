"""
設定管理モジュール
"""
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BotConfig:
    """Discord botの設定を管理するクラス"""
    
    def __init__(self, character_name: str):
        """
        初期化
        
        Args:
            character_name: このボットが演じるキャラクターの名前
        """
        # 基本設定
        self.character_name = character_name
        self.notion_character_name = character_name
        
        # 環境変数から設定を読み込み
        self.channel_id = int(os.environ.get('CHANNEL_ID', '0'))
        self.min_response_delay = int(os.environ.get('MIN_RESPONSE_DELAY', '5'))
        self.max_response_delay = int(os.environ.get('MAX_RESPONSE_DELAY', '15'))
        self.max_conversation_turns = int(os.environ.get('MAX_CONVERSATION_TURNS', '10'))
        
        # データディレクトリのパス
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 基本ロールスクリプトのパス
        self.base_role_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'config', 
            'base_role.txt'
        )
        
        # ボット応答ガイダンスのパス
        self.bot_guidance_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'bot_response_guidance.txt'
        )
        
        # 設定をロギング
        self._log_config()
        
    def _log_config(self):
        """設定をログに記録"""
        logger.info(f"Character name: {self.character_name}")
        logger.info(f"Channel ID: {self.channel_id}")
        logger.info(f"Min response delay: {self.min_response_delay}")
        logger.info(f"Max response delay: {self.max_response_delay}")
        logger.info(f"Max conversation turns: {self.max_conversation_turns}")
        
    def load_base_role(self) -> str:
        """基本ロールスクリプトを読み込む"""
        try:
            with open(self.base_role_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"基本ロールスクリプトの読み込みに失敗: {e}")
            return "あなたはDiscordチャットに参加するAIボットです。会話の流れに自然に応答し、常にキャラクターを維持してください。"
            
    def load_bot_response_guidance(self) -> str:
        """ボット応答ガイダンスを読み込む"""
        try:
            with open(self.bot_guidance_path, 'r', encoding='utf-8') as f:
                guidance = f.read().strip()
                logger.info("Bot response guidance loaded successfully")
                return guidance
        except Exception as e:
            logger.error(f"Failed to load bot response guidance: {e}")
            # ファイル読み込み失敗時のフォールバックテキスト
            return """
                現在、あなたは他のAIボットからの質問に応答しています。以下のガイドラインに従ってください：
                1. 「ご指摘の通りですね」「おっしゃる通りです」などの同意から始めないでください
                2. 質問に直接答え、相手の発言内容を先に知っていたかのような表現は避けてください
                3. 自分の考えや意見を述べる際は、「私は〜と考えます」「私の見解では〜」などの表現を使ってください
                4. 会話の自然な流れを維持しつつ、不自然な「先読み」を避けてください
                """