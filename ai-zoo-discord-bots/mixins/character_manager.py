"""
キャラクター管理ミックスイン
"""
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class CharacterManagerMixin:
    """キャラクターの設定と管理を担当するミックスイン"""
    
    async def load_character_settings(self):
        """Notionからキャラクター設定を読み込む"""
        logger.info(f"Looking up character settings for Notion character name: {self.config.notion_character_name}")
        
        try:
            # Notionからキャラクター設定を取得するために、インスタンス変数notion_serviceを使用
            self.character = await self.notion_service.get_character(self.config.notion_character_name)
            
            if not self.character:
                logger.warning(f"Character {self.config.notion_character_name} not found in Notion. Using default settings.")
                self.character = {
                    "name": self.config.notion_character_name,
                    "personality": "Friendly and helpful",
                    "speaking_style": "Casual and conversational",
                    "language": "English",
                    "model": "gpt-4"
                }
            
            # キャラクター設定をシステムプロンプトにフォーマット
            self.system_prompt = self.notion_service.format_character_prompt(
                self.character,
                base_role=self.base_role
            )
            
            actual_name = self.character.get("name", self.config.notion_character_name)
            logger.info(f"Character settings loaded successfully:")
            logger.info(f"- Discord display name: {self.config.character_name}")
            logger.info(f"- Notion character name: {self.config.notion_character_name}")
            logger.info(f"- Actual name from Notion: {actual_name}")
            logger.info(f"- Model: {self.character.get('model', 'unknown')}")
            logger.info(f"- Base role loaded: {bool(self.base_role)}")
            
        except Exception as e:
            logger.error(f"Failed to load character settings: {e}")
            # デフォルト設定を設定
            self.character = {
                "name": self.config.notion_character_name,
                "personality": "Friendly and helpful",
                "speaking_style": "Casual and conversational",
                "language": "English",
                "model": "gpt-4"
            }
            # 基本ロールがある場合は使用し、なければ簡単なデフォルトプロンプトを使用
            if self.base_role:
                self.system_prompt = f"You are {self.config.notion_character_name}.\n\n{self.base_role}"
            else:
                self.system_prompt = f"You are {self.config.notion_character_name}. Be friendly and helpful."
    
    def _adjust_system_prompt_for_sender(self, sender_name: str) -> str:
        """
        送信者に基づいてシステムプロンプトを調整する
        
        Args:
            sender_name: メッセージの送信者名
            
        Returns:
            調整されたシステムプロンプト
        """
        # 基本のシステムプロンプト
        adjusted_prompt = self.system_prompt
        
        # 送信者が他のボットかどうかを確認
        bot_names = ['gpt-4o-animal', 'claude-animal', 'gpt-4o', 'claude']
        if any(bot_name.lower() in sender_name.lower() for bot_name in bot_names):
            # ボット応答ガイダンスを読み込み
            bot_response_guidance = self.config.load_bot_response_guidance()
            adjusted_prompt += bot_response_guidance
            
        return adjusted_prompt
    
    def generate_introduction_message(self) -> str:
        """
        キャラクター設定に基づいてボット紹介メッセージを生成する
        
        Returns:
            フォーマットされた紹介メッセージ
        """
        intro_parts = []
        
        # 挨拶を追加
        intro_parts.append(f"こんにちは！私は{self.config.character_name}です。")
        
        # 性格を追加
        if self.character and "personality" in self.character:
            intro_parts.append(f"性格: {self.character['personality']}")
        
        # 話し方を追加
        if self.character and "speaking_style" in self.character:
            intro_parts.append(f"話し方: {self.character['speaking_style']}")
        
        # 興味・関心を追加
        if self.character and "interests" in self.character:
            interests = self.character["interests"]
            if isinstance(interests, list):
                interests_str = "、".join(interests)
            else:
                interests_str = interests
            intro_parts.append(f"興味・関心: {interests_str}")
        
        # 背景がある場合は追加
        if self.character and "background" in self.character:
            intro_parts.append(f"背景: {self.character['background']}")
        
        # モデル情報を追加
        if self.character and "model" in self.character:
            intro_parts.append(f"使用モデル: {self.character['model']}")
        
        # 子クラスで追加情報を設定できるようにするためのフックメソッド
        additional_info = self.get_additional_introduction_info()
        if additional_info:
            intro_parts.append(additional_info)
        
        # チャットへの招待を追加
        intro_parts.append("気軽に話しかけてください！")
        
        return "\n".join(intro_parts)
    
    def get_additional_introduction_info(self) -> Optional[str]:
        """
        紹介メッセージの追加情報を取得する
        子クラスでオーバーライドして、カスタム紹介情報を追加できる
        
        Returns:
            追加情報の文字列またはNone
        """
        return None
        
    def _extract_character_keywords(self) -> List[str]:
        """
        キャラクター設定から重要なキーワードを抽出する
        
        Returns:
            キャラクターに関連するキーワードのリスト
        """
        keywords = []
        
        if self.character:
            # 性格からキーワードを抽出
            if 'personality' in self.character:
                personality = self.character['personality']
                keywords.extend(personality.split())
                
            # 話し方からキーワードを抽出
            if 'speaking_style' in self.character:
                speaking_style = self.character['speaking_style']
                keywords.extend(speaking_style.split())
                
            # 興味・関心からキーワードを抽出
            if 'interests' in self.character:
                interests = self.character['interests']
                if isinstance(interests, list):
                    keywords.extend(interests)
                else:
                    keywords.extend(interests.split())
        
        # 重複を除去して返す
        return list(set(keywords))