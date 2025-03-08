"""
Base Discord bot implementation for AI Zoo.
This serves as a foundation for all bot implementations.
"""
import os
import logging
import asyncio
import random
import discord
from discord.ext import commands
from typing import Optional, Dict, Any, List

from utils.config_loader import get_env, load_env_vars
from utils.conversation import ConversationManager
from utils.random_delay import delay_response, simulate_typing
from services.llm_service import LLMService
from services.notion_service import NotionService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaseDiscordBot(commands.Bot):
    """Base Discord bot for AI Zoo."""
    
    def __init__(self, 
                character_name: str,
                command_prefix: str = "!",
                intents: Optional[discord.Intents] = None):
        """
        Initialize the base bot.
        
        Args:
            character_name: Name of the character this bot will play
            command_prefix: Command prefix for bot commands
            intents: Discord intents for the bot
        """
        # Set up intents
        if intents is None:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.messages = True
            
        super().__init__(command_prefix=command_prefix, intents=intents)
        
        # Bot configuration
        self.character_name = character_name
        self.channel_id = int(os.environ.get('CHANNEL_ID', '0'))
        self.min_response_delay = int(os.environ.get('MIN_RESPONSE_DELAY', '5'))
        self.max_response_delay = int(os.environ.get('MAX_RESPONSE_DELAY', '15'))
        self.max_conversation_turns = int(os.environ.get('MAX_CONVERSATION_TURNS', '10'))
        
        # Initialize services
        self.llm_service = LLMService()
        self.notion_service = NotionService()
        
        # Initialize conversation manager
        self.conversation_manager = ConversationManager()
        
        # Character settings
        self.character: Optional[Dict[str, Any]] = None
        self.system_prompt: Optional[str] = None
        
        # Cooldown tracking
        self.in_cooldown = False
        self.cooldown_until = 0
        
        # Register event handlers
        self.setup_events()
    
    def setup_events(self):
        """Set up Discord event handlers."""
        @self.event
        async def on_ready():
            logger.info(f"Bot {self.character_name} logged in as {self.user}")
            
            # Load character settings from Notion
            await self.load_character_settings()
            
            # Join the specified channel
            if self.channel_id:
                channel = self.get_channel(self.channel_id)
                if channel:
                    logger.info(f"Joined channel: {channel.name}")
                    
                    # Generate and send introduction message
                    intro_message = self.generate_introduction_message()
                    await channel.send(intro_message)
                    logger.info(f"Sent introduction message to channel: {channel.name}")
                else:
                    logger.error(f"Could not find channel with ID: {self.channel_id}")
        
        @self.event
        async def on_message(message):
            # Ignore messages from self
            if message.author == self.user:
                return
                
            # Only respond in the specified channel
            if self.channel_id and message.channel.id != self.channel_id:
                return
                
            # Process commands first
            await self.process_commands(message)
            
            # Don't respond to commands
            if message.content.startswith(self.command_prefix):
                return
                
            # Check if we're in cooldown
            if self.in_cooldown:
                return
                
            # Add message to conversation history
            self.conversation_manager.add_message(
                author=message.author.display_name,
                content=message.content
            )
            
            # Check if we should respond based on conversation turns
            if self.conversation_manager.should_cool_down(self.max_conversation_turns):
                logger.info(f"Cooling down after {self.max_conversation_turns} conversation turns")
                self.in_cooldown = True
                self.conversation_manager.reset_conversation_turns()
                
                # Set cooldown for a random time between 5-15 minutes
                cooldown_minutes = random.randint(5, 15)
                self.cooldown_until = asyncio.get_event_loop().time() + (cooldown_minutes * 60)
                
                # Schedule cooldown reset
                asyncio.create_task(self.reset_cooldown_after(cooldown_minutes))
                return
            
            # 子クラスで実装するメソッドを呼び出す（フックメソッド）
            if self.should_respond_to_message(message):
                # Generate and send response
                asyncio.create_task(self.respond_to_message(message))
    
    # フックメソッド - 子クラスでオーバーライド可能
    def should_respond_to_message(self, message) -> bool:
        """
        Determine if the bot should respond to a message.
        Override this in subclasses to implement custom response logic.
        
        Args:
            message: Discord message to check
            
        Returns:
            True if the bot should respond, False otherwise
        """
        return True
    
    async def load_character_settings(self):
        """Load character settings from Notion."""
        logger.info(f"Loading character settings for {self.character_name}")
        
        try:
            # Get character settings from Notion
            self.character = await self.notion_service.get_character(self.character_name)
            
            if not self.character:
                logger.warning(f"Character {self.character_name} not found in Notion. Using default settings.")
                self.character = {
                    "name": self.character_name,
                    "personality": "Friendly and helpful",
                    "speaking_style": "Casual and conversational",
                    "language": "English",
                    "model": "gpt-4"
                }
            
            # Format character settings into system prompt
            self.system_prompt = self.notion_service.format_character_prompt(self.character)
            logger.info(f"Character settings loaded for {self.character_name}")
            
        except Exception as e:
            logger.error(f"Failed to load character settings: {e}")
            # Set default character settings
            self.character = {
                "name": self.character_name,
                "personality": "Friendly and helpful",
                "speaking_style": "Casual and conversational",
                "language": "English",
                "model": "gpt-4"
            }
            self.system_prompt = f"You are {self.character_name}. Be friendly and helpful."
    
    async def respond_to_message(self, message):
        """
        Generate and send a response to a message.
        
        Args:
            message: Discord message to respond to
        """
        try:
            # Add random delay to simulate thinking/typing
            await delay_response(self.min_response_delay, self.max_response_delay)
            
            # Get model from character settings or default to gpt-4
            model = self.character.get("model", "gpt-4") if self.character else "gpt-4"
            
            # Format conversation history for LLM
            if model.startswith("gpt"):
                messages = self.conversation_manager.format_for_openai(self.system_prompt)
            else:
                messages = self.conversation_manager.format_for_anthropic(self.system_prompt)
            
            # Simulate typing
            message_length = random.randint(50, 200)  # Estimate response length
            await simulate_typing(message.channel, message_length)
            
            # Generate response from LLM
            response = await self.llm_service.generate_response(
                messages=messages,
                model=model
            )
            
            # Add bot's response to conversation history
            self.conversation_manager.add_message(
                author=self.character_name,
                content=response,
                bot_name=self.character_name
            )
            
            # Send response
            await message.channel.send(response)
            
        except Exception as e:
            logger.error(f"Failed to respond to message: {e}")
    
    async def reset_cooldown_after(self, minutes: int):
        """
        Reset cooldown after specified minutes.
        
        Args:
            minutes: Number of minutes to cooldown
        """
        logger.info(f"Cooling down for {minutes} minutes")
        await asyncio.sleep(minutes * 60)
        self.in_cooldown = False
        logger.info("Cooldown ended")
    
    def generate_introduction_message(self) -> str:
        """
        Generate bot introduction message based on character settings.
        
        Returns:
            Formatted introduction message
        """
        intro_parts = []
        
        # Add greeting
        intro_parts.append(f"こんにちは！私は{self.character_name}です。")
        
        # Add personality
        if self.character and "personality" in self.character:
            intro_parts.append(f"性格: {self.character['personality']}")
        
        # Add speaking style
        if self.character and "speaking_style" in self.character:
            intro_parts.append(f"話し方: {self.character['speaking_style']}")
        
        # Add interests
        if self.character and "interests" in self.character:
            interests = self.character["interests"]
            if isinstance(interests, list):
                interests_str = "、".join(interests)
            else:
                interests_str = interests
            intro_parts.append(f"興味・関心: {interests_str}")
        
        # Add background if available
        if self.character and "background" in self.character:
            intro_parts.append(f"背景: {self.character['background']}")
        
        # Add model info
        if self.character and "model" in self.character:
            intro_parts.append(f"使用モデル: {self.character['model']}")
        
        # 子クラスで追加情報を設定できるようにするためのフックメソッド
        additional_info = self.get_additional_introduction_info()
        if additional_info:
            intro_parts.append(additional_info)
        
        # Add invitation to chat
        intro_parts.append("気軽に話しかけてください！")
        
        return "\n".join(intro_parts)
    
    # フックメソッド - 子クラスでオーバーライド可能
    def get_additional_introduction_info(self) -> Optional[str]:
        """
        Get additional information for the introduction message.
        Override this in subclasses to add custom introduction information.
        
        Returns:
            Additional information string or None
        """
        return None
    
    async def send_scheduled_message(self, message: str):
        """
        Send a scheduled message to the channel.
        
        Args:
            message: Message to send
        """
        if not self.channel_id:
            logger.error("No channel ID specified for scheduled message")
            return
            
        channel = self.get_channel(self.channel_id)
        if not channel:
            logger.error(f"Could not find channel with ID: {self.channel_id}")
            return
            
        await channel.send(message)
        logger.info(f"Sent scheduled message: {message}")
