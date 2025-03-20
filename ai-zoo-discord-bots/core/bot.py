"""
Discord Botの基本実装
すべてのボット実装の基礎となるコアクラス
"""
import os
import logging
import asyncio
import discord
from discord.ext import commands
from typing import Optional, Dict, Any

from core.config import BotConfig
from utils.conversation import ConversationManager
from services.llm_service import LLMService
from services.notion_service import NotionService
from services.database import init_db
from mixins.character_manager import CharacterManagerMixin
from mixins.conversation_handler import ConversationHandlerMixin
from mixins.utility_function import UtilityFunctionMixin

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BaseDiscordBot(commands.Bot, CharacterManagerMixin, ConversationHandlerMixin, UtilityFunctionMixin):
    """AI Zooのベース Discord Bot"""
    
    def __init__(self, 
                character_name: str,
                command_prefix: str = "!",
                intents: Optional[discord.Intents] = None):
        """
        ベースボットを初期化

        Args:
            character_name: このボットが演じるキャラクターの名前
            command_prefix: ボットコマンドのプレフィックス
            intents: ボットのDiscordインテント
        """
        # インテントのセットアップ
        if intents is None:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.messages = True
            
        # 親クラスの初期化
        super().__init__(command_prefix=command_prefix, intents=intents)
        
        # 設定の初期化
        self.config = BotConfig(character_name)
        
        # 基本ロールの読み込み
        self.base_role = self.config.load_base_role()
        
        # サービスの初期化
        self.llm_service = LLMService()
        self.notion_service = NotionService()
        
        # 会話マネージャーの初期化
        self.conversation_manager = ConversationManager()
        
        # キャラクター設定
        self.character: Optional[Dict[str, Any]] = None
        self.system_prompt: Optional[str] = None
        
        # 会話処理の初期設定
        self.setup_conversation_handling()
        
        # 効用関数の初期化
        self.initialize_utility_function()
        
        # データベース初期化（拡張ロギング付き）
        self.db_initialized = False
        logger.info("データベース初期化を開始...")
        try:
            init_task = asyncio.create_task(self._init_database())
            init_task.add_done_callback(
                lambda t: logger.info(f"データベース初期化タスク完了: {t.result() if not t.exception() else t.exception()}")
            )
            logger.info("データベース初期化タスク作成完了")
        except Exception as e:
            logger.error(f"データベース初期化タスクの作成に失敗: {e}", exc_info=True)
        
        # イベントハンドラの設定
        self.setup_events()
    
    async def _init_database(self):
        """データベースを初期化"""
        logger.info("_init_databaseメソッドに入りました")
        try:
            logger.info("データベースの初期化を試みます...")
            # データベース初期化処理の結果を確認
            success = await init_db()
            if success:
                logger.info("データベース初期化が正常に完了しました")
                self.db_initialized = True
                return True
            else:
                logger.error("データベース初期化がFalseを返しました")
                self.db_initialized = False
                return False
        except Exception as e:
            logger.error(f"データベース初期化が例外で失敗: {e}", exc_info=True)
            self.db_initialized = False
            return False
        finally:
            logger.info(f"データベース初期化ステータス: {self.db_initialized}")
    
    def setup_events(self):
        """Discordイベントハンドラを設定"""
        @self.event
        async def on_ready():
            logger.info(f"Botが {self.user} としてログインしました")
            
            # Notionからキャラクター設定を読み込み
            await self.load_character_settings()
            
            # 指定されたチャンネルに参加
            if self.config.channel_id:
                channel = self.get_channel(self.config.channel_id)
                if channel:
                    logger.info(f"チャンネルに参加: {channel.name}")
                    
                    # 紹介メッセージを生成して送信
                    intro_message = self.generate_introduction_message()
                    await channel.send(intro_message)
                    logger.info(f"紹介メッセージをチャンネルに送信: {channel.name}")
                else:
                    logger.error(f"ID {self.config.channel_id} のチャンネルが見つかりません")
        
        @self.event
        async def on_message(message):
            # メッセージ処理の委譲
            await self.process_message(message)