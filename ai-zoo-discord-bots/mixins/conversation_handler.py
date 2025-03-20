"""
会話処理を担当するミックスインクラス
"""
import os
import time
import asyncio
import logging
import random
from typing import Dict, Any, List, Optional, Union

from utils.random_delay import delay_response, simulate_typing
from utils.url_content_fetcher import process_message_urls

logger = logging.getLogger(__name__)

class ConversationHandlerMixin:
    """会話の処理と応答生成を担当するミックスインクラス"""
    
    def setup_conversation_handling(self):
        """会話処理の初期設定を行う"""
        # クールダウントラッキング
        self.in_cooldown = False
        self.cooldown_until = 0
    
    async def respond_to_message(self, message):
        """
        メッセージに対して応答を生成して送信する
        
        Args:
            message: 応答するDiscordメッセージ
        """
        try:
            start_time = time.time()
            
            # ランダムな遅延を追加して考え中/入力中をシミュレート
            await delay_response(self.config.min_response_delay, self.config.max_response_delay)
            delay_time = time.time() - start_time
            
            # キャラクター設定からモデルを取得するか、デフォルトとしてgpt-4を使用
            model = self.character.get("model", "gpt-4") if self.character else "gpt-4"
            
            # 送信者に基づいてシステムプロンプトを動的に調整
            adjusted_system_prompt = self._adjust_system_prompt_for_sender(message.author.display_name)
            
            # LLM用に会話履歴をフォーマット
            format_start_time = time.time()
            if model.startswith("gpt"):
                messages = self.conversation_manager.format_for_openai(adjusted_system_prompt)
            else:
                messages = self.conversation_manager.format_for_anthropic(adjusted_system_prompt)
            format_time = time.time() - format_start_time
            
            # LLMから応答を生成
            llm_start_time = time.time()
            responses = await self.llm_service.generate_response(
                messages=messages,
                model=model,
                bot_name=self.config.character_name,
                skip_logging=not self.db_initialized,
                n=3  # 複数の応答候補を生成
            )
            llm_time = time.time() - llm_start_time
            
            # コンテキスト情報を準備
            context = {
                "author": message.author.display_name,
                "channel": message.channel.name if hasattr(message.channel, 'name') else "DM",
                "content": message.content,
                "conversation_history": self.conversation_manager.get_recent_history(5)
            }
            
            # 複数の応答候補が返された場合は効用関数で選択、そうでなければ単一応答を使用
            if isinstance(responses, list) and len(responses) > 1:
                response = self.select_optimal_response(responses, context)
                logger.info(f"Selected optimal response from {len(responses)} candidates")
            else:
                response = responses[0] if isinstance(responses, list) else responses
            
            # データベースの状態をログに記録
            if not self.db_initialized:
                logger.warning("Database not initialized, skipping request logging")
                
            # 応答の文字数を計算
            response_length = len(response)
            
            # タイピングをシミュレート
            typing_start_time = time.time()
            # 文章の長さに基づいてタイピングシミュレーション
            typing_duration, typing_speed = await simulate_typing(message.channel, response_length)
            typing_time = time.time() - typing_start_time
            
            # 会話履歴にボットの応答を追加
            history_start_time = time.time()
            channel_name = message.channel.name if hasattr(message.channel, 'name') else "DM"
            self.conversation_manager.add_message(
                author=self.config.character_name,
                content=response,
                bot_name=self.config.character_name,
                channel_name=channel_name
            )
            history_time = time.time() - history_start_time
            
            # 応答を送信
            send_start_time = time.time()
            await message.channel.send(response)
            send_time = time.time() - send_start_time
            
            # タイミング情報をログに記録
            total_time = time.time() - start_time
            logger.info(f"Message response timing breakdown:")
            logger.info(f"  - Initial Delay: {delay_time:.2f} seconds")
            logger.info(f"  - Message Formatting: {format_time:.2f} seconds")
            logger.info(f"  - LLM Generation: {llm_time:.2f} seconds")
            logger.info(f"  - Typing Simulation: {typing_time:.2f} seconds (speed: {typing_speed} chars/min, text length: {response_length} chars)")
            logger.info(f"  - History Update: {history_time:.2f} seconds")
            logger.info(f"  - Message Sending: {send_time:.2f} seconds")
            logger.info(f"  - Total Processing: {total_time:.2f} seconds")
            
        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"Failed to respond to message after {error_time:.2f} seconds: {e}", exc_info=True)
    
    async def process_message(self, message):
        """
        受信メッセージを処理する
        
        Args:
            message: 処理するDiscordメッセージ
        """
        # 自分自身のメッセージは無視
        if message.author == self.user:
            return
            
        # 指定されたチャンネルでのみ応答
        if self.config.channel_id and message.channel.id != self.config.channel_id:
            return
            
        # コマンドを最初に処理
        await self.process_commands(message)
        
        # コマンドには応答しない
        if message.content.startswith(self.command_prefix):
            return
            
        # クールダウン中かチェック
        if self.in_cooldown:
            return
        
        # メッセージをチャンネル名付きで会話履歴に追加
        channel_name = message.channel.name if hasattr(message.channel, 'name') else "DM"
        self.conversation_manager.add_message(
            author=message.author.display_name,
            content=message.content,
            channel_name=channel_name
        )
        
        # メッセージ内のURLを処理
        try:
            url_content = await process_message_urls(
                message.content,
                max_urls=3,  # 処理する最大URL数
                max_length_per_url=1000  # URL毎の最大文字数
            )
            
            # URLコンテンツがある場合は会話履歴に追加
            if url_content:
                logger.info(f"Adding URL content from message by {message.author.display_name}")
                self.conversation_manager.add_url_content(
                    related_author=message.author.display_name,
                    content=url_content
                )
        except Exception as e:
            logger.error(f"Error processing URLs in message: {e}", exc_info=True)
            
        # 会話ターン数に基づいてクールダウンが必要かチェック
        if self.conversation_manager.should_cool_down(self.config.max_conversation_turns):
            logger.info(f"Cooling down after {self.config.max_conversation_turns} conversation turns")
            self.in_cooldown = True
            self.conversation_manager.reset_conversation_turns()
            
            # 1-3分のランダムな時間でクールダウンを設定
            cooldown_minutes = random.randint(1, 3)
            self.cooldown_until = asyncio.get_event_loop().time() + (cooldown_minutes * 60)
            
            # クールダウンリセットをスケジュール
            asyncio.create_task(self.reset_cooldown_after(cooldown_minutes))
            return
        
        # 応答すべきかを子クラスのメソッドで判断（フック）
        if self.should_respond_to_message(message):
            # 応答を生成して送信
            asyncio.create_task(self.respond_to_message(message))
    
    # フックメソッド - 子クラスでオーバーライド可能
    def should_respond_to_message(self, message) -> bool:
        """
        ボットがメッセージに応答すべきかを判断する
        カスタム応答ロジックを実装するために子クラスでオーバーライドする
        
        Args:
            message: チェックするDiscordメッセージ
            
        Returns:
            応答すべき場合はTrue、そうでなければFalse
        """
        return True
            
    async def reset_cooldown_after(self, minutes: int):
        """
        指定された分数後にクールダウンをリセットする
        
        Args:
            minutes: クールダウンする分数
        """
        logger.info(f"Cooling down for {minutes} minutes")
        await asyncio.sleep(minutes * 60)
        self.in_cooldown = False
        logger.info("Cooldown ended")
        
    async def send_scheduled_message(self, message: str):
        """
        スケジュールされたメッセージをチャンネルに送信する
        
        Args:
            message: 送信するメッセージ
        """
        if not self.config.channel_id:
            logger.error("No channel ID specified for scheduled message")
            return
            
        channel = self.get_channel(self.config.channel_id)
        if not channel:
            logger.error(f"Could not find channel with ID: {self.config.channel_id}")
            return
            
        await channel.send(message)
        logger.info(f"Sent scheduled message: {message}")